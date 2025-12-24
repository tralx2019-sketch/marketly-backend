from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()

app = Flask(__name__)

# ========== إعدادات MySQL ==========
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:@localhost/marketly_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'marketly-secret-key-2025')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)

# تهيئة الإضافات
CORS(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Gemini AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyA264jNcQX-r85K78ZYi50JGFyBQKysoSY')
genai.configure(api_key=GOOGLE_API_KEY)

# ========== تعريف الجداول ==========

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    campaigns = db.relationship('Campaign', backref='user', lazy=True)

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    target_audience = db.Column(db.String(200))
    keywords = db.Column(db.String(200))
    platform = db.Column(db.String(100))
    tone = db.Column(db.String(100))
    generated_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ======= إنشاء الجداول ==========

def create_tables():
    """خلينا نعمل الجداول في الداتابيز لو مش موجودين"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ تم إنشاء الجداول في قاعدة البيانات MySQL")
    except Exception as e:
        print(f"❌ ياهندسة حصل غلط في إنشاء الجداول: {e}")

# ======== نقاط النهاية ========

@app.route('/auth/register', methods=['POST'])
def register():
    """تسجيل مستخدم جديد"""
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        # يا هندسة  متسبنيش أحط بيانات فاضية
        if not name or not email or not password:
            return jsonify({"error": "الاسم والبريد وكلمة السر مطلوبين"}), 400
        
        # نتأكد إن الإيميل مش متسجل قبل كده
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "الإيميل موجود بالفعل"}), 400
        
        # نشفر الباسورد علشان محدش يعرفها
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # نعمل توكن للمستخدم الجديد
        access_token = create_access_token(identity=str(new_user.id))
        return jsonify({
            "message": "تم إنشاء الحساب بنجاح",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email
            },
            "token": access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "عذراً السيرڤر مش شغال دلوقتي"}), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """تسجيل دخول المستخدم"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        # يا هندسة مفيش تسجيل دخول من غير إيميل وباسورد
        if not email or not password:
            return jsonify({"error": "البريد وكلمة السر مطلوبين"}), 400

        # نبحث عن المستخدم في الداتابيز
        user = User.query.filter_by(email=email).first()
        
        # لو ملقناهوش أو الباسورد غلط
        if not user or not bcrypt.check_password_hash(user.password, password):
            return jsonify({"error": "البريد أو كلمة السر غير صحيحة"}), 401

        # نعمل توكن جديد
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "message": "تم تسجيل الدخول بنجاح",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "token": access_token
        }), 200
        
    except Exception as e:
        return jsonify({"error": "السيرڤر بيقول مش قادر دلوقتي"}), 500

@app.route('/auth/update', methods=['PUT'])
@jwt_required()
def update_user():
    """تحديث بيانات المستخدم - الجديدة دي"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        # نجيب المستخدم من الداتابيز
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "المستخدم مش موجود"}), 404
        
        # نتأكد من البيانات الأساسية
        new_name = data.get('name')
        new_email = data.get('email')
        
        if not new_name or not new_email:
            return jsonify({"error": "الاسم والبريد مطلوبين"}), 400
        
        # لو غير الإيميل نتأكد إنه مش متكرر
        if new_email != user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email:
                return jsonify({"error": "الإيميل الجديد موجود بالفعل"}), 400
        
        # لو عايز يغير الباسورد
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if current_password and new_password:
            # نتأكد إن الباسورد القديم صح
            if not bcrypt.check_password_hash(user.password, current_password):
                return jsonify({"error": "كلمة السر الحالية غلط"}), 401
            
            # نشفر الباسورد الجديد
            hashed_new_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_new_password
        
        # نحدث البيانات
        user.name = new_name
        user.email = new_email
        db.session.commit()
        
        return jsonify({
            "message": "تم تحديث بياناتك بنجاح",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "مش قادرين نحدث البيانات دلوقتي"}), 500

@app.route('/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_content():
    """توليد محتوى بالذكاء الاصطناعي - PROMPT """
    try:
        data = request.json
        product_name = data.get('productName', '')
        description = data.get('description', '')
        platform = data.get('platform', 'فيسبوك')
        tone = data.get('tone', 'احترافي (شركات وبزنس)')
        target_audience = data.get('targetAudience', '')
        keywords = data.get('keywords', '')
        
        # يا هندسة مش هنعمل محتوى من غير منتج ووصف
        if not product_name or not description:
            return jsonify({"error": "اسم المنتج والوصف مطلوبان"}), 400
        
        prompt = f"""
        **أنت خبير تسويق رقمي محترف في وكالة إعلانات رائدة.**
        
        **مهمتك:** إنشاء محتوى تسويقي احترافي وجذاب تماماً وجاهز للنشر.
        
        **تفاصيل الحملة:**
        - المنتج/الخدمة: {product_name}
        - وصف المنتج: {description}
        - المنصة المستهدفة: {platform}
        - نبرة المحتوى: {tone}
        - الجمهور المستهدف: {target_audience if target_audience else "عام"}
        - الكلمات المفتاحية: {keywords if keywords else "غير محددة"}
        
        **تعليمات دقيقة للغاية:**
        1. ابدأ بمقدمة قوية وجذابة تلفت الانتباه (3-4 جمل)
        2. قسم المحتوى إلى أقسام واضحة باستخدام ترويسات فرعية
        3. استخدم لغة عربية فصيحة مع مراعاة اللهجة {tone}
        4. أضف إيموجيز مناسبة 🚀✨🔥💡 في أماكن استراتيجية
        5. استخدم هاشتاجات #مناسبة وجذابة في النهاية
        6. أنهِ بدعوة واضحة للعمل (Call to Action) قوية
        7. اجعل المحتوى يبدو حديثاً وعصرياً وجاهزاً للنشر مباشرة
        
        **الشكل المطلوب للمحتوى:**
        - محتوى منظم بشكل احترافي
        - فقرات قصيرة وجذابة
        - نقاط واضحة عندما يكون مناسباً
        - لغة مقنعة وتفاعلية
        - مناسب تماماً لمنصة {platform}
        
        **تأكد من:**
        - جودة المحتوى كأنه كتب بواسطة كاتب محتوى محترف
        - تناسق النبرة مع {tone}
        - جاذبية المحتوى للجمهور المستهدف
        - احترافية وجودة عالية
        
        **لا تكرر المعلومات، بل قدم محتوى أصلياً وإبداعياً.**
        """
        
        # نكلم Gemini AI
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content(prompt)
        
        # لو الرد جه
        #  نخزنه في الداتابيز
        if response.text:
            # تنظيف النص من علامات الاقتباس الزائدة
            cleaned_text = response.text.strip()
            cleaned_text = cleaned_text.replace('**', '')  # نزيل علامات البولد الزائدة
            cleaned_text = cleaned_text.replace('*', '')   # نزيل علامات النجمة
            
            current_user_id = get_jwt_identity()
            if current_user_id:
                try:
                    new_campaign = Campaign(
                        user_id=current_user_id,
                        product_name=product_name,
                        description=description,
                        target_audience=target_audience,
                        keywords=keywords,
                        platform=platform,
                        tone=tone,
                        generated_content=cleaned_text
                    )
                    db.session.add(new_campaign)
                    db.session.commit()
                    return jsonify({
                        "result": cleaned_text,
                        "campaign_id": new_campaign.id,
                        "saved": True
                    })
                except Exception as db_error:
                    # لو حصل غلط في الحفظ نرجع المحتوى بس منغير حفظ
                    return jsonify({"result": cleaned_text, "saved": False})
            
            # لو مش مسجل دخول نرجع المحتوى بس
            return jsonify({"result": cleaned_text, "saved": False})
        else:
            return jsonify({"error": "الـ AI مش عارف يكتب حاجة"}), 500

    except Exception as e:
        return jsonify({"error": f"يا هندسة حصل غلط: {str(e)}"}), 500

@app.route('/campaigns', methods=['GET'])
@jwt_required()
def get_campaigns():
    """جلب كل حملات المستخدم"""
    try:
        current_user_id = get_jwt_identity()
        campaigns = Campaign.query.filter_by(user_id=current_user_id)\
            .order_by(Campaign.created_at.desc())\
            .all()
        
        # نهيء البيانات علشان الـ frontend
        campaigns_list = []
        for campaign in campaigns:
            campaigns_list.append({
                "id": campaign.id,
                "product_name": campaign.product_name,
                "platform": campaign.platform,
                "tone": campaign.tone,
                "generated_content": campaign.generated_content,
                "created_at": campaign.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return jsonify(campaigns_list), 200
        
    except Exception as e:
        return jsonify({"error": "مش قادرين نجيب الحملات دلوقتي"}), 500

@app.route('/campaigns/<int:campaign_id>', methods=['DELETE'])
@jwt_required()
def delete_campaign(campaign_id):
    """حذف حملة معينة"""
    try:
        current_user_id = get_jwt_identity()
        campaign = Campaign.query.filter_by(id=campaign_id, user_id=current_user_id).first()
        if not campaign:
            return jsonify({"error": "مفيش حملة بالرقم ده"}), 404
        
        db.session.delete(campaign)
        db.session.commit()
        return jsonify({"message": "تم مسح الحملة"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "مش قادرين نمسح الحملة دلوقتي"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """فحص صحة السيرفر - عشان نتأكد إنه شغال"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            "status": "شغال زي الفل",
            "database": "MySQL متصل",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
    except Exception as e:
        return jsonify({
            "status": "مش شغال",
            "database": "MySQL مش متصل"
        }), 500

# ========== تشغيل التطبيق ==========

if __name__ == '__main__':
    create_tables()
    print("=" * 50)
    print("🚀 Marketly AI Server is running on http://localhost:5000")
    print("📊 Database: MySQL (marketly_db)")
    print("👤 Test User: test@marketly.com / 123456")
    print("🆕 Added: /auth/update endpoint for settings")
    print("✨ IMPROVED: Enhanced AI prompt for better content generation")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port)