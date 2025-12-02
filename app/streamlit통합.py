import streamlit as st
import pandas as pd
import plotly.express as px
import os
import hashlib
import json
from preprocess_reading_excel import main as preprocess_main

# 초기 세팅
#--------------------------------------------
st.set_page_config(layout="wide") #화면에 꽉차게
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

#제목 설정
st.title("🌳 학생별 레벨 성장 그래프") 

# Hash 계산 함수
# 파일이 기존에 업로드한 파일과 동알한지 판단하기 위함
# --------------------------------------------
def get_file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


# session_state 초기화
if "df" not in st.session_state:
    st.session_state.df = None

if "current_file" not in st.session_state:
    st.session_state.current_file = None



# 파일 업로드
#----------------------------------------------------------------------------------
uploaded_file = st.file_uploader("원본 엑셀 파일을 업로드하세요 (.xlsx)", type=["xlsx"])

# Cloud에서도 input/output 폴더 자동 생성
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)

# 새로운 파일이 업로드된 경우만 처리하기
if uploaded_file and (uploaded_file.name != st.session_state.current_file):

    raw_name = uploaded_file.name
    raw_path = os.path.join("input", raw_name)

    with open(raw_path, "wb") as f:
        f.write(uploaded_file.read())

    st.session_state.current_file = uploaded_file.name  # 현재 업로드된 파일 기록
    st.toast(f"파일 업로드 완료: {raw_name}", icon="📂")

    # 전처리 후 파일명 설정
    root_name = raw_name.replace(".xlsx", "")
    processed_path = f"output/{root_name}_processed.xlsx" #원본 파일명 반영하기
    hash_path = f"output/{root_name}_hash.json"

    # 새 파일 해시 계산
    new_hash = get_file_hash(raw_path)

    # 이전 해시 로드
    if os.path.exists(hash_path):
        old_hash = json.load(open(hash_path))["hash"]
    else:
        old_hash = None

    # 전처리 필요 여부 판단
    if new_hash == old_hash and os.path.exists(processed_path):
        st.toast(f"이미 전처리된 파일입니다 → {processed_path}", icon="✅")
    else:
        st.toast("새로운 파일 감지 → 전처리 실행합니다.", icon="⚙️")
        with st.spinner("전처리 중입니다... 잠시만 기다려주세요!"):
            preprocess_main(raw_path)

        # # 기본 파일명으로 생성된 전처리 결과를 우리가 원하는 파일명으로 이동
        # if os.path.exists("output/전처리파일테스트.xlsx"):
        #     os.replace("output/전처리파일테스트.xlsx", processed_path)

        # 전처리 함수 실행 후 생성된 파일 확인
        default_processed = "output/전처리파일.xlsx"

        if os.path.exists(default_processed):
            os.replace(default_processed, processed_path)
        else:
            st.error("❌ 전처리 결과 파일이 생성되지 않았습니다.")
            st.stop()


        json.dump({"hash": new_hash}, open(hash_path, "w"))
        st.toast(f"전처리 완료! 저장된 파일: {processed_path}", icon="🎉")

    # 전처리된 파일 로드 → session_state에 저장
    # df = pd.read_excel(processed_path)
    # 전처리된 파일 로드 전 파일 존재 여부 체크
    if not os.path.exists(processed_path):
        st.error(f"❌ 전처리된 파일을 찾을 수 없습니다: {processed_path}")
        st.stop()

    df = pd.read_excel(processed_path, engine="openpyxl")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values(["이름", "순번"])

    st.session_state.df = df
    st.toast("전처리된 파일을 불러왔습니다.", icon="📁")



# 화면 출력 (session_state.df 있을 때)
# -----------------------------------
if st.session_state.df is not None:

    df = st.session_state.df

    # 학생 선택 리스트
    students = df["이름"].dropna().unique()
    student = st.selectbox("학생을 선택하세요:", students)

    tmp = df[df["이름"] == student]

    # 그래프 색상 매핑
    color_map = {
        "리더스": "#355C7D",       # 딥블루
        "그림책": "#F67280",       # 딥핑크
        "그림리더스": "#6C5B7B",   # 퍼플-그레이
        "챕터북": "#99B898",        # 부드러운 민트
        "소설": "#E84A5F",          # 레드핑크 
        0: "#C06C84",               # 로즈톤
        "기타": "#B0BEC5"          # 회색 (NaN)
    }


    # 레벨 성장 라인 그래프
    # --------------------------------------------
    #툴팁 설정 (마우스 올리면 보이는 정보)
    fig = px.scatter(
        tmp,
        x="순번",
        y="레벨",
        color="구분",
        symbol="구분",
        hover_data=["Date", "책제목", "구분", "시리즈"],
        color_discrete_map=color_map,
    )

    #그래프 스타일 설정
    fig.update_traces(
        mode="lines+markers", #점 + 선으로 표시
        line=dict(width=4), #선 두께
        marker=dict(size=10), #점 크기 설정
    )

    #y축 설정
    fig.update_yaxes(
        type="category", #숫자가 아닌 범주로
        categoryorder="array",
        categoryarray=["-1", "0", "1", "2", "3", "4", "5", "6"], #-1~6으로 처리 (여기서 -1은 nan 값을 대체한 값)
    )


    #레이아웃 설정
    fig.update_layout(
        title=f"{student} 학생의 레벨 변화 추이",
        xaxis_title="읽은 순번",
        yaxis_title="레벨",
        legend_title="구분",
        title_font=dict(size=28),
    )

    # 파이차트
    # --------------------------------------------
    pie = tmp["구분"].value_counts().reset_index()
    pie.columns = ["구분", "count"]

    pie_fig = px.pie(
        pie,
        names="구분",
        values="count",
        color="구분",
        color_discrete_map=color_map,
        title=f"{student} 학생의 구분별 책 비율",
    )
    pie_fig.update_traces(textinfo="percent+label")


    # 화면 레이아웃
    col1, col2 = st.columns([8, 2]) #그래프 8대2로 설정

    with col1:
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.plotly_chart(pie_fig, use_container_width=True)

else:
    st.info("전처리된 파일이 없습니다. 먼저 파일을 업로드해주세요.")
