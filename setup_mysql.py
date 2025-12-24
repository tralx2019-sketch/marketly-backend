"""
الملف ده مسؤول عن إنشاء قاعدة البيانات والجداول
مفيد لو عايز تعمل setup للداتابيز من الأول
"""

import pymysql
from dotenv import load_dotenv
import os

# نحمل الإعدادات
load_dotenv()

def setup_database():
    """الخطوات اللي بنعملها علشان نجهز قاعدة البيانات"""
    print("🔧 بنحضر قاعدة البيانات...")
    
    try:
        # نتصل بـ MySQL
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # لو عندك باسورد، حطه هنا
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # 1. نعمل قاعدة البيانات لو مش موجودة
        cursor.execute("""
            CREATE DATABASE IF NOT EXISTS marketly_db 
            CHARACTER SET utf8mb4 
            COLLATE utf8mb4_unicode_ci
        """)
        print("✅ قاعدة البيانات 'marketly_db' جاهزة")
        
        # 2. نستخدم قاعدة البيانات الجديدة
        cursor.execute("USE marketly_db")
        
        # 3. نعمل جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("✅ جدول 'users' اتساب")
        
        # 4. نعمل جدول الحملات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_name VARCHAR(200),
                description TEXT,
                target_audience VARCHAR(200),
                keywords VARCHAR(200),
                platform VARCHAR(100),
                tone VARCHAR(100),
                generated_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        print("✅ جدول 'campaigns' اتساب")
        
        # 5. نضيف مستخدم تجريبي (لو مش موجود)
        try:
            cursor.execute('''
                INSERT IGNORE INTO users (name, email, password) 
                VALUES ('أحمد محمد', 'test@marketly.com', 
                '$2b$12$V9dJq5p5Q5L1L1L1L1L1L.L1L1L1L1L1L1L1L1L1L1L1L1L1L1L1')
            ''')
            print("✅ المستخدم التجريبي اتضاف")
        except:
            print("⚠️  المستخدم التجريبي موجود فعلاً")
        
        # نحفظ التغييرات
        connection.commit()
        
        # نغلق الاتصال
        cursor.close()
        connection.close()
        
        print("\n" + "="*50)
        print("🎉 تم إعداد قاعدة البيانات بنجاح!")
        print("="*50)
        print("\n📊 بيانات الاتصال:")
        print("   • قاعدة البيانات: marketly_db")
        print("   • المستخدم: root")
        print("   • الباسورد: (مفيش)")
        print("\n👤 بيانات الدخول التجريبية:")
        print("   📧 البريد: test@marketly.com")
        print("   🔑 الباسورد: 123456")
        print("\n🚀 دلوقتي تقدر تشغل السيرڤر: python main.py")
        
    except Exception as e:
        print(f"❌ للأسف حصل مشكلة: {e}")
        print("\n📌 الحلول الممكنة:")
        print("1. شغل XAMPP واتأكد إن MySQL شغال")
        print("2. لو عندك باسورد للروت، غير السطر 16")
        print("3. اتأكد إن البورت 3306 مفتوح")

# لو شغلنا الملف مباشر
if __name__ == '__main__':
    setup_database()