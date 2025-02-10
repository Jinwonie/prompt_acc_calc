########## Import ##########
import re
import streamlit as st
from imghdr import what
from conf import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from src import image_accuracy_calculator, load_df, image_formatter

########## Main ##########
if __name__ == "__main__":
    st.set_page_config(page_title="프롬프트 정확도 측정기", page_icon="📜", layout="centered")

    st.header("📜 프롬프트 정확도 측정기")
    st.image(Config.ORG_IMG_DIR, width=500)

    if "name" not in st.session_state:
        st.session_state["name"] = ""
    if "phone_num" not in st.session_state:
        st.session_state["phone_num"] = ""

    with st.form("input_data"):
        name = st.text_input("이름을 입력해주세요", value=st.session_state["name"]).strip()
        phone_num = st.text_input("전화번호를 입력해주세요(우승자 상품 제공 용도로 활용됩니다.) 형식: 01012345678", value=st.session_state["phone_num"]).strip()
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
            try:
                with st.spinner("정확도 측정 중...", show_time=True):
                    engine = create_engine(st.secrets["DATABASE_URL"])

                    acc = image_accuracy_calculator(Config.ORG_IMG_DIR, image)
                    binary_data = image.getvalue()

                    # 기존 데이터 확인 쿼리
                    check_sql = text("""
                        SELECT acc FROM image_acc WHERE usr_nm = :usr_nm AND phone_num = :phone_num
                    """)

                    insert_sql = text("""
                        INSERT INTO image_acc (usr_nm, phone_num, acc, img_data)
                        VALUES (:usr_nm, :phone_num, :acc, :img_data)
                    """)

                    update_sql = text("""
                        UPDATE image_acc SET acc = :acc, img_data = :img_data
                        WHERE usr_nm = :usr_nm AND phone_num = :phone_num
                    """)

                    with engine.begin() as conn:
                        result = conn.execute(check_sql, {"usr_nm": name, "phone_num": phone_num}).fetchone()

                        if result is None:
                            # 기존 데이터가 없으면 INSERT
                            conn.execute(insert_sql, {
                                "usr_nm": name,
                                "phone_num": phone_num,
                                "acc": float(acc),
                                "img_data": binary_data
                            })
                        elif result[0] < float(acc):
                            # 기존 데이터가 있고, 새로운 acc가 더 높은 경우 UPDATE
                            conn.execute(update_sql, {
                                "usr_nm": name,
                                "phone_num": phone_num,
                                "acc": float(acc),
                                "img_data": binary_data
                            })

                    # Streamlit 세션 상태 저장
                    st.session_state["acc"] = acc
                    st.session_state["name"] = name
                    st.session_state["phone_num"] = phone_num

                    st.rerun()

            except SQLAlchemyError as e:
                st.error(f"❌ 데이터베이스 오류: {e}")

    if ("name" in st.session_state and st.session_state.name) and ("acc" in st.session_state and st.session_state.acc):
        get_name = st.session_state.get("name", "")
        score = st.session_state.get("acc", "")
        st.write("")
        st.write(f"{get_name}님의 프롬프트 점수는 {score}% 입니다.")

    select_sql = "SELECT * FROM image_acc"
    df = load_df(st.secrets["DATABASE_URL"], select_sql)
    if len(df) > 0:
        st.write("")
        st.write("현재 랭킹👑")
        df["img_data"] = df["img_data"].apply(image_formatter)
        df.columns = [["이름", "점수", "이미지"]]
        df.insert(0, "등수", df.index + 1)  # 등수 컬럼 추가
    
        # HTML 테이블 생성
        table_html = "<table><tr><th>등수</th><th>이름</th><th>점수</th><th>이미지</th></tr>"
        for _, row in df.iterrows():
            table_html += f"<tr><td>{row['등수']}</td><td>{row['이름']}</td><td>{row['점수']}%</td><td>{row['이미지']}</td></tr>"
        table_html += "</table>"

        # Streamlit에서 HTML로 출력
        st.markdown(table_html, unsafe_allow_html=True)
