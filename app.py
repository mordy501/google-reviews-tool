import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import uuid
from io import BytesIO
from lxml import etree
import random
import html

st.set_page_config(page_title="Google Reviews XML Generator", layout="centered")
st.title("🔧 توليد رابط تقييمات Google Merchant")

st.markdown("""
✨ *ارفع ملف التقييمات، وأدخل رابط فيد المنتجات من المتجر، وخذ رابط XML النهائي لرفعه في Google Merchant.*
""")

def safe(value):
    return html.escape(str(value)) if value else ""

# رفع ملف التقييمات
uploaded_file = st.file_uploader("📄 ارفع ملف التقييمات (Excel)", type=["xlsx"])
feed_url = st.text_input("🔗 أدخل رابط فيد المنتجات (XML)")

# الوظيفة الأساسية
if uploaded_file and feed_url:
    try:
        df = pd.read_excel(uploaded_file)

        # التحقق من الأعمدة الأساسية
        required_cols = ["product_name", "review_content", "rating", "reviewer"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"❌ تأكد أن ملف التقييمات يحتوي على الأعمدة التالية: {', '.join(required_cols)}")
            st.stop()

        # تحميل الفيد وتحليله
        feed_resp = requests.get(feed_url)
        feed_tree = etree.fromstring(feed_resp.content)
        items = feed_tree.xpath("//item")

        # تجهيز قاموس للبحث السريع
        products = {}
        for item in items:
            title_el = item.find("{http://base.google.com/ns/1.0}title")
            id_el = item.find("{http://base.google.com/ns/1.0}id")
            if title_el is not None and id_el is not None:
                products[title_el.text.strip()] = id_el.text.strip()

        reviews_data = []
        unmatched = []

        for _, row in df.iterrows():
            product_name = str(row["product_name"]).strip()
            rating = int(row["rating"])
            content = str(row["review_content"])
            reviewer = str(row["reviewer"])

            matched_product_id = products.get(product_name)
            if matched_product_id:
                random_days_ago = random.randint(0, 60)
                random_date = datetime.now() - timedelta(days=random_days_ago)

                reviews_data.append({
                    "review_id": str(uuid.uuid4()),
                    "reviewer": reviewer,
                    "review_timestamp": random_date.strftime("%Y-%m-%dT%H:%M:%S"),
                    "title": "",
                    "content": content,
                    "review_rating": rating,
                    "product_id": matched_product_id
                })
            else:
                unmatched.append(product_name)

        if unmatched:
            st.warning(f"⚠️ المنتجات التالية لم يتم العثور عليها في الفيد:\n- " + "\n- ".join(unmatched))

        # توليد ملف XML
        root = ET.Element("reviews")
        for review in reviews_data:
            r = ET.SubElement(root, "review")
            ET.SubElement(r, "review_id").text = safe(review["review_id"])
            reviewer_el = ET.SubElement(r, "reviewer")
            ET.SubElement(reviewer_el, "name").text = safe(review["reviewer"])
            ET.SubElement(r, "review_timestamp").text = safe(review["review_timestamp"])
            ET.SubElement(r, "title").text = safe(review["title"])
            ET.SubElement(r, "content").text = safe(review["content"])
            ET.SubElement(r, "review_rating").text = safe(review["review_rating"])
            product_ids_el = ET.SubElement(r, "product_ids")
            ET.SubElement(product_ids_el, "product_id").text = safe(review["product_id"])

        # تحويل XML إلى بايتات
        xml_bytes = BytesIO()
        tree = ET.ElementTree(root)
        tree.write(xml_bytes, encoding="utf-8", xml_declaration=True)

        st.success("✅ تم توليد التقييمات بنجاح!")
        st.download_button("📥 تحميل ملف XML", data=xml_bytes.getvalue(), file_name="reviews.xml", mime="application/xml")

    except Exception as e:
        st.error(f"حدث خطأ: {str(e)}")
