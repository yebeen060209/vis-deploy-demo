"""서울 자치구별 따릉이 이용 대시보드 (12주차 배포 예제를 내 주제로 바꾼 판).

GitHub 저장소에 app.py, requirements.txt, ddareungi_summary.csv, ddareungi_stations.csv를
같은 폴더로 올리고 Community Cloud의 Main file path에 app.py를 적습니다.
두 CSV는 prep.py가 원본(이용정보 CSV + 대여소 정보 xlsx)에서 만든 요약 파일입니다.
내 컴퓨터에서 실행: python -m streamlit run app.py
"""
# Path: app.py가 있는 폴더를 찾을 때 씁니다. 배포에서 가장 중요한 줄의 재료입니다.
from pathlib import Path

# font_manager: 서버에 한글 글꼴이 있는지 찾을 때 씁니다.
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter
import plotly.express as px
# streamlit: 앱 화면을 만듭니다. 서버에서도 내 컴퓨터와 똑같이 app.py를 위에서 아래로 실행합니다.
import streamlit as st

# app.py가 있는 폴더. 배포 서버의 작업 폴더와 다를 수 있어 파일은 이 폴더 기준으로 찾습니다.
HERE = Path(__file__).parent

# 화면 지표 이름 → (표 열 이름, 단위). "대여소당"은 아래에서 계산해 만드는 열입니다.
METRICS = {
    "이용건수": ("이용건수", "건"),
    "대여소당 월평균 이용건수": ("대여소당", "건"),
    "총 이동거리": ("이동거리_km", "km"),
    "탄소 절감량": ("탄소량_kg", "kg"),
}
# 한글 글꼴이 없을 때 Matplotlib 가로축 이름에 쓰는 영어 표현입니다.
METRICS_EN = {
    "이용건수": "Trips", "대여소당 월평균 이용건수": "Trips per station (monthly avg)",
    "총 이동거리": "Total distance (km)", "탄소 절감량": "CO2 saved (kg)",
}
AGE_ORDER = ["~10대", "20대", "30대", "40대", "50대", "60대", "70대이상", "기타"]
SEX_ORDER = ["남", "여", "미상"]
SEX_COLORS = {"남": "#0072B2", "여": "#D55E00", "미상": "#999999"}
BAR_COLOR = "#0072B2"
# 한글 글꼴이 없는 서버에서 Matplotlib 그림의 자치구 이름을 영어로 바꿔 쓰기 위한 표입니다.
ROMAN = {
    "강남구": "Gangnam", "강동구": "Gangdong", "강북구": "Gangbuk", "강서구": "Gangseo", "관악구": "Gwanak",
    "광진구": "Gwangjin", "구로구": "Guro", "금천구": "Geumcheon", "노원구": "Nowon", "도봉구": "Dobong",
    "동대문구": "Dongdaemun", "동작구": "Dongjak", "마포구": "Mapo", "서대문구": "Seodaemun",
    "서초구": "Seocho", "성동구": "Seongdong", "성북구": "Seongbuk", "송파구": "Songpa",
    "양천구": "Yangcheon", "영등포구": "Yeongdeungpo", "용산구": "Yongsan", "은평구": "Eunpyeong",
    "종로구": "Jongno", "중구": "Jung", "중랑구": "Jungnang",
}

# 브라우저 탭 이름과 넓은 화면을 정합니다.
st.set_page_config(page_title="따릉이 자치구 탐색", layout="wide")


# 결과를 기억해 두어 위젯을 바꿔도 CSV를 다시 읽지 않습니다.
@st.cache_data
def load_data():
    summary = pd.read_csv(HERE / "ddareungi_summary.csv")
    stations = pd.read_csv(HERE / "ddareungi_stations.csv")
    return summary, stations


# Matplotlib은 서버가 그림을 만들어, 서버에 한글 글꼴이 없으면 글자가 □로 나옵니다.
# 그래서 쓸 수 있는 한글 글꼴을 먼저 찾고, 없으면 None을 돌려줍니다.
def korean_font():
    """Matplotlib가 쓸 수 있는 한글 글꼴 이름. 없으면 None(배포 서버에는 없을 수 있습니다)."""
    names = {f.name for f in fm.fontManager.ttflist}
    return next((f for f in ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"] if f in names), None)


# 첫 화면에 질문을 제목으로 둡니다(프로젝트 평가: 질문·데이터).
st.title("따릉이는 어느 자치구에서 가장 많이 탈까?")
# 출처, 기간, 단위를 밝힙니다.
st.caption("출처: 서울 열린데이터광장 '서울시 공공자전거 따릉이 이용정보(월별)'·'대여소 정보'(공공누리 1유형, 서울특별시) "
           "· 2026년 1~6월 · 대여소 번호로 자치구를 연결해 합계를 냈습니다.")

# 요약 CSV가 없거나 이름이 다르면 오류 대신 안내를 보이고 멈춥니다.
try:
    summary, stations = load_data()
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 ddareungi_summary.csv, ddareungi_stations.csv를 올려 주세요. "
             "(prep.py로 만듭니다)")
    st.stop()

# 위젯 세 개: 여러 개 고르기 / 범위 슬라이더 / 하나 고르기
st.sidebar.header("조회 조건")
# 기본값은 전체 기간 이용건수가 많은 5개 구입니다.
top5 = summary.groupby("자치구")["이용건수"].sum().nlargest(5).index.tolist()
# 여러 개 고르기: 고른 자치구의 리스트
gus = st.sidebar.multiselect("자치구", sorted(summary["자치구"].unique()), default=top5)
# 범위 슬라이더: (시작 연월, 끝 연월). "2026-01" 같은 글자는 순서대로 비교됩니다.
month_list = sorted(summary["연월"].unique())
start, end = st.sidebar.select_slider("기간", options=month_list, value=(month_list[0], month_list[-1]))
# 하나 고르기: 고른 지표 이름
metric_label = st.sidebar.selectbox("표시 지표", list(METRICS))
col, unit = METRICS[metric_label]

# 위젯 선택 → view → 숫자·차트·표·CSV가 모두 같은 view를 씁니다.
# 고른 자치구(isin)와 기간(between)의 행만 남긴 표입니다.
view = summary.loc[summary["자치구"].isin(gus) & summary["연월"].between(start, end)]
# 자치구를 모두 지우면 view가 빕니다. 안내 뒤 멈추지 않으면 아래 계산에서 오류가 납니다.
if view.empty:
    st.warning("표시할 데이터가 없습니다. 자치구를 하나 이상 선택하세요.")
    st.stop()

# 자치구 x 연월 표: 성별·연령대를 합치고, 그 달 이용 대여소 수를 붙입니다.
gm = (view.groupby(["자치구", "연월"], as_index=False)[["이용건수", "이동거리_km", "탄소량_kg"]].sum()
      .merge(stations, on=["자치구", "연월"], how="left"))
# 대여소당 이용건수 = 이용건수 ÷ 그 달 이용 대여소 수. 대여소가 많은 구가 유리해 보이는 것을 덜어 냅니다.
gm["대여소당"] = gm["이용건수"] / gm["대여소수"]

# 자치구별 기간 합계 표. 대여소당은 달마다 비율을 평균 내지 않고 "이용건수 합계 ÷ (대여소 수의 월 합계)"로 구합니다.
by_gu = gm.groupby("자치구", as_index=False).agg(
    이용건수=("이용건수", "sum"), 이동거리_km=("이동거리_km", "sum"),
    탄소량_kg=("탄소량_kg", "sum"), 대여소월=("대여소수", "sum"))
by_gu["대여소당"] = by_gu["이용건수"] / by_gu["대여소월"]
n_months = view["연월"].nunique()

st.subheader(f"{start} ~ {end} · {metric_label} · 자치구 {len(gus)}곳")
# 카드 세 개를 나란히 놓습니다. 대여소당 지표는 합계가 아니라 평균이라 이름을 달리합니다.
if col == "대여소당":
    c1_label = f"기간 {metric_label}"
    c1_value = by_gu["이용건수"].sum() / by_gu["대여소월"].sum()
else:
    c1_label = f"기간 {metric_label} 합계"
    c1_value = by_gu[col].sum()
c1, c2, c3 = st.columns(3)
c1.metric(c1_label, f"{c1_value:,.0f} {unit}")
c2.metric("월평균 이용 대여소", f"{by_gu['대여소월'].sum() / n_months:,.0f} 개")
# 건당 평균 이동거리 = 이동거리 합계 ÷ 이용건수 합계. 행마다의 평균을 다시 평균 내지 않습니다.
c3.metric("건당 평균 이동거리", f"{by_gu['이동거리_km'].sum() / by_gu['이용건수'].sum():.2f} km")
st.caption("이용 대여소는 그 달에 이용 기록이 한 번이라도 있는 대여소입니다. "
           "탄소 절감량은 이동거리 기준으로 서울시가 산출한 값이며, 값이 비어 있는 일부 행은 합계에서 빠집니다.")

# 질문에 대한 답을 한 줄로 보입니다. 고른 구가 둘 이상일 때만 의미가 있습니다.
if len(by_gu) > 1:
    most = by_gu.loc[by_gu["이용건수"].idxmax(), "자치구"]
    densest = by_gu.loc[by_gu["대여소당"].idxmax(), "자치구"]
    if most == densest:
        st.info(f"선택한 구 중 **{most}**가 이용건수와 대여소당 월평균 이용건수 모두 가장 많습니다.")
    else:
        st.info(f"선택한 구 중 이용건수는 **{most}**, 대여소 하나당 월평균 이용건수는 **{densest}**가 가장 많습니다. "
                "두 순위가 다른 것은 구마다 대여소 수가 다르기 때문일 수 있습니다.")

# 차트 1: 월별 추이. Plotly는 보는 사람의 브라우저가 글자를 그려 한글이 그대로 보입니다.
trend = px.line(gm.sort_values(["자치구", "연월"]), x="연월", y=col, color="자치구", markers=True,
                title=f"월별 추이: {metric_label}",
                labels={"연월": "연월", col: f"{metric_label} ({unit})", "자치구": "자치구"})
trend.update_yaxes(rangemode="tozero")
# 구가 여러 개여도 그림이 좁아지지 않게 범례를 아래에 둡니다.
trend.update_layout(legend=dict(orientation="h", y=-0.25, title_text=""))

# 차트 2: 자치구 비교. Matplotlib는 서버가 그림을 만들어 서버에 한글 글꼴이 있어야 합니다.
kfont = korean_font()
# 값이 큰 구가 위로 오도록 오름차순으로 정렬해 가로 막대를 그립니다.
ranked = by_gu.sort_values(col)
# 한글 글꼴이 없으면 자치구 이름을 영어로 바꿔 글자가 □로 깨지지 않게 합니다.
names = ranked["자치구"] if kfont else ranked["자치구"].map(ROMAN)
with plt.rc_context({"font.family": kfont or "DejaVu Sans", "axes.unicode_minus": False}):
    static_fig, ax = plt.subplots(figsize=(6, max(3.6, 0.32 * len(ranked) + 1.4)))
    bars = ax.barh(names, ranked[col], color=BAR_COLOR)
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in ranked[col]], padding=3)
    if kfont:
        ax.set(title="자치구 비교 (기간 전체)", xlabel=f"{metric_label} ({unit})")
    else:   # 한글 글꼴이 없는 서버: 글자가 □로 깨지지 않게 영어로 씁니다
        ax.set(title="District comparison (whole period)", xlabel=METRICS_EN[metric_label])
    ax.set_xlim(0, max(ranked[col].max() * 1.18, 1))
    # 1e6 같은 과학 표기 대신 2,000,000처럼 천 단위 쉼표로 보입니다.
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.spines[["top", "right"]].set_visible(False)
    static_fig.tight_layout()

# 차트 3: 누가 타는가. 고른 구·기간의 이용건수를 연령대와 성별로 나눕니다.
who = view.groupby(["연령대", "성별"], as_index=False)["이용건수"].sum()
who_fig = px.bar(who, x="연령대", y="이용건수", color="성별", barmode="group",
                 category_orders={"연령대": AGE_ORDER, "성별": SEX_ORDER}, color_discrete_map=SEX_COLORS,
                 title="연령대·성별 이용건수", labels={"이용건수": "이용건수 (건)"})
who_fig.update_layout(legend=dict(orientation="h", y=-0.25, title_text=""))
who_fig.update_yaxes(rangemode="tozero")

# 차트 세 개를 세 칸에 나란히 놓습니다(프로젝트 최소 요건: 차트 3개 이상).
left, middle, right = st.columns(3)
with left:
    st.plotly_chart(trend, width="stretch")
with middle:
    st.pyplot(static_fig, width="stretch")
with right:
    st.plotly_chart(who_fig, width="stretch")
# 다 쓴 Matplotlib 그림을 닫습니다.
plt.close(static_fig)
# 서버에 한글 글꼴이 없어 영어로 그렸다면 그 사실을 화면에 알립니다.
if not kfont:
    st.caption("이 서버에는 한글 글꼴이 없어 가운데 그림(Matplotlib)의 글자를 영어로 표시합니다.")
st.caption("원자료에서 성별이 입력되지 않은 이용(전체의 약 25%)은 '미상'으로 표시합니다.")

st.subheader("현재 선택한 데이터")
# 한 행은 한 자치구·한 달입니다. 고른 행을 표로 보입니다.
table = gm.rename(columns={"대여소수": "이용 대여소 수", "대여소당": "대여소당 이용건수"}).round(
    {"이동거리_km": 1, "탄소량_kg": 1, "대여소당 이용건수": 1})
st.dataframe(table, hide_index=True, width="stretch")
# 지금 고른 데이터를 CSV로 내려받습니다. utf-8-sig는 엑셀 한글 깨짐을 막습니다.
st.download_button("현재 선택 CSV 저장", data=table.to_csv(index=False).encode("utf-8-sig"),
                   file_name="selected_ddareungi.csv", mime="text/csv")
st.caption("이 자료만으로 이용량 차이의 원인(대여소 위치, 인구, 지형, 날씨 등)을 단정하지 않습니다.")
