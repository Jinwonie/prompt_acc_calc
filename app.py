import os
import re
import sqlite3
import streamlit as st
from imghdr import what
from conf import Config
from dotenv import load_dotenv
from src import image_accuracy_calculator, load_df, image_formatter

load_dotenv()

if __name__ == "__main__":
    st.set_page_config(page_title="프롬프트 정확도 측정기", page_icon="📜", layout="centered")

    st.header("📜 프롬프트 정확도 측정기")
    st.image(Config.ORG_IMG_DIR, width=500)

    if "name" not in st.session_state:
        st.session_state["name"] = ""
    if "phone_num" not in st.session_state:
        st.session_state["phone_num"] = ""

    with st.form("input_data"):
        name = st.text_input("이름을 입력해주세요", value=st.session_state["name"])
        phone_num = st.text_input("전화번호를 입력해주세요", value=st.session_state["phone_num"])
        image = st.file_uploader("이미지를 업로드해주세요.", type=["png", "jpg", "jpeg"])

        submit = st.form_submit_button("정확도 측정하기")

    if submit:
        if not name or not phone_num or not image:
            st.warning("⚠️ 모든 필드를 입력해야 합니다!")
        elif not re.match("^[a-zA-Z가-힣 ]+$", name):
            st.warning("⚠️ 이름은 한글 또는 영문 문자만 입력해주세요!")
        elif not re.match(r"^01[0-9]{8,9}$", phone_num):
            st.warning("⚠️ 올바른 전화번호 형식을 입력하세요!")
        elif what(None, h=image.getvalue()) not in ["jpeg", "png"]:
            st.warning("⚠️ 지원되지 않는 이미지 형식입니다!")
        elif len(image.getvalue()) > 5 * 1024 * 1024:
            st.warning("⚠️ 파일 크기가 너무 큽니다! (최대 5MB)")
        else:
            db_path = os.path.abspath(Config.SQL_DIR)
            if not db_path.startswith(os.path.abspath("safe_db_directory")):
                st.error("❌ 잘못된 데이터베이스 접근입니다!")
            else:
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    real_acc = image_accuracy_calculator(Config.ORG_IMG_DIR, image)
                    binary_data = image.getvalue()
                    data = (name, phone_num, real_acc, binary_data)

                    cursor.execute("""
                    INSERT INTO image_acc (usr_nm, phone_num, acc, img_data)
                        VALUES (?, ?, ?, ?);
                    """, data)
                    conn.commit()

                    st.session_state["name"] = name
                    st.session_state["phone_num"] = phone_num

                    st.success("✅ 데이터가 성공적으로 저장되었습니다!")
                    st.rerun()
                except sqlite3.DatabaseError as e:
                    conn.rollback()
                    st.error(f"❌ 데이터베이스 오류: {e}")
                finally:
                    conn.close()
