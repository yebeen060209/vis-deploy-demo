"""12주차 배포 예제 앱: 11주차 대시보드를 웹에 올릴 수 있게 정리한 판.

GitHub 저장소에 이 파일, requirements.txt, sales.csv를 같은 폴더로 올리고
Community Cloud의 Main file path에 app.py(하위 폴더에 두었다면 그 경로)를 적습니다.
개인 프로젝트에서는 sales.csv 대신 출처가 분명한 공개 데이터를 씁니다(수업 예제 데이터 제외).
내 컴퓨터에서 실행: python -m streamlit run app.py
"""
# Path: app.py가 있는 폴더를 찾을 때 씁니다. 배포에서 가장 중요한 줄의 재료입니다.
from pathlib import Path

# font_manager: 서버에 한글 글꼴이 있는지 찾을 때 씁니다.
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
# streamlit: 앱 화면을 만듭니다. 서버에서도 내 컴퓨터와 똑같이 app.py를 위에서 아래로 실행합니다.
import streamlit as st

# app.py가 있는 폴더. 배포 서버의 작업 폴더(저장소 맨 위)와 다를 수 있어 파일은 이 폴더 기준으로 찾습니다.
# __file__은 app.py의 경로, .parent는 그 폴더입니다. 서버에서는 저장소 안 app.py의 폴더가 됩니다.
HERE = Path(__file__).parent
COLORS = {"A": "#0072B2", "B": "#D55E00"}

# 브라우저 탭 이름과 넓은 화면을 정합니다.
st.set_page_config(page_title="지점 실적 탐색", layout="wide")


# 결과를 기억해 두어 위젯을 바꿔도 CSV를 다시 읽지 않습니다.
@st.cache_data
# HERE / "sales.csv": app.py 옆의 파일. C:/Users/… 같은 내 컴퓨터 경로를 쓰면 서버에서 못 찾습니다(1-3).
def load_data():
    return pd.read_csv(HERE / "sales.csv")


# Matplotlib은 서버가 그림을 만들어, 서버에 한글 글꼴이 없으면 글자가 □로 나옵니다.
# 그래서 쓸 수 있는 한글 글꼴을 먼저 찾고, 없으면 None을 돌려줍니다.
def korean_font():
    """Matplotlib가 쓸 수 있는 한글 글꼴 이름. 없으면 None(배포 서버에는 없을 수 있습니다)."""
    names = {f.name for f in fm.fontManager.ttflist}
    return next((f for f in ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"] if f in names), None)


# 첫 화면에 질문을 제목으로 둡니다(프로젝트 평가: 질문·데이터).
st.title("어느 지점의 실적이 더 좋은가")
# 출처, 기간, 단위를 밝힙니다.
st.caption("출처: 수업용 가상 데이터(sales.csv) · 2026년 1~12월 지점별 월 실적 · 금액 단위: 백만원")

# 저장소에 sales.csv를 올리지 않았거나 이름이 다르면 오류 대신 안내를 보이고 멈춥니다.
try:
    data = load_data()
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 sales.csv를 올려 주세요.")
    st.stop()

# 여기부터 11주차와 같은 위젯 세 개입니다.
st.sidebar.header("조회 조건")
# 여러 개 고르기: 고른 지점의 리스트
branches = st.sidebar.multiselect("지점", ["A", "B"], default=["A", "B"])
# 범위 슬라이더: (시작 월, 끝 월)
months = st.sidebar.slider("월 범위", 1, 12, (1, 12))
# 하나 고르기: 고른 지표 이름
metric_label = st.sidebar.selectbox("표시 지표", ["매출", "영업이익"])
# 화면 이름(매출)을 표의 열 이름(sales)으로 바꿉니다.
metric = {"매출": "sales", "영업이익": "profit"}[metric_label]

# 위젯 선택 → view → 숫자·차트·표·CSV가 모두 같은 view를 씁니다.
# 고른 지점(isin)과 월 범위(between)의 행만 남긴 표입니다.
view = data.loc[data["branch"].isin(branches) & data["month"].between(months[0], months[1])].copy()
# 지점을 모두 지우면 view가 빕니다. 안내 뒤 멈추지 않으면 아래 계산에서 오류가 납니다.
if view.empty:
    st.warning("표시할 데이터가 없습니다. 지점을 하나 이상 선택하세요.")
    st.stop()

st.subheader(f"{months[0]}~{months[1]}월 {metric_label} · {', '.join(branches)}지점")
# 카드 세 개를 나란히 놓습니다.
c1, c2, c3 = st.columns(3)
c1.metric(f"기간 {metric_label} 합계", f"{view[metric].sum():,.0f} 백만원")
c2.metric("표시 관측 수", f"{len(view)} 행")
# 기간 영업이익률 = 기간 이익 합계 ÷ 기간 매출 합계 × 100. 달마다의 비율을 평균 내지 않습니다.
c3.metric("기간 영업이익률", f"{view['profit'].sum() / view['sales'].sum() * 100:.1f} %")
st.caption("한 행은 한 달·한 지점입니다. 영업이익률은 기간 이익 합계 ÷ 기간 매출 합계입니다.")

# 차트 1: 월별 추이. Plotly는 보는 사람의 브라우저가 글자를 그려 한글이 그대로 보입니다.
# 차트 1(Plotly): 보는 사람의 브라우저가 글자를 그려 서버에 글꼴이 없어도 한글이 보입니다.
trend = px.line(view.sort_values(["branch", "month"]), x="month", y=metric, color="branch",
                markers=True, color_discrete_map=COLORS, title="월별 추이",
                labels={"month": "월", metric: f"{metric_label} (백만원)", "branch": "지점"})
trend.update_xaxes(dtick=1)
trend.update_yaxes(rangemode="tozero")

# 차트 2: 기간 합계. Matplotlib는 서버가 그림을 만들어 서버에 한글 글꼴이 있어야 합니다.
# 차트 2(Matplotlib): 서버에 한글 글꼴이 있는지 먼저 봅니다.
kfont = korean_font()
# 지점별 기간 합계 표
totals = view.groupby("branch", as_index=False)[metric].sum()
# 한글 글꼴이 있으면 그 글꼴로, 없으면 기본 글꼴(DejaVu Sans)로 그립니다.
with plt.rc_context({"font.family": kfont or "DejaVu Sans", "axes.unicode_minus": False}):
    static_fig, ax = plt.subplots(figsize=(6, 3.6))
    bars = ax.bar(totals["branch"], totals[metric], color=[COLORS[b] for b in totals["branch"]])
    ax.bar_label(bars, fmt="%.0f", padding=3)
    # 한글 글꼴이 있을 때만 한글 제목을 씁니다.
    if kfont:
        ax.set(title="기간 합계", xlabel="지점", ylabel=f"{metric_label} (백만원)")
    else:   # 한글 글꼴이 없는 서버: 글자가 □로 깨지지 않게 영어로 씁니다
        ax.set(title="Period total", xlabel="Branch", ylabel=f"{metric} (million KRW)")
    ax.set_ylim(0, max(totals[metric].max() * 1.2, 1))
    ax.spines[["top", "right"]].set_visible(False)
    static_fig.tight_layout()

# 차트 3: 기간 영업이익률(Plotly)
# 차트 3(Plotly): 지점별 매출과 이익의 기간 합계로 이익률을 계산합니다.
period = view.groupby("branch", as_index=False)[["sales", "profit"]].sum()
period["margin"] = period["profit"] / period["sales"] * 100
margin_fig = px.bar(period, x="branch", y="margin", color="branch", color_discrete_map=COLORS,
                    title="기간 영업이익률", labels={"branch": "지점", "margin": "영업이익률 (%)"})
margin_fig.update_layout(showlegend=False)
margin_fig.update_yaxes(rangemode="tozero")

# 차트 세 개를 세 칸에 나란히 놓습니다(프로젝트 최소 요건: 차트 3개 이상).
left, middle, right = st.columns(3)
with left:
    st.plotly_chart(trend, width="stretch")
with middle:
    st.pyplot(static_fig, width="stretch")
with right:
    st.plotly_chart(margin_fig, width="stretch")
# 다 쓴 Matplotlib 그림을 닫습니다.
plt.close(static_fig)
# 서버에 한글 글꼴이 없어 영어로 그렸다면 그 사실을 화면에 알립니다.
if not kfont:
    st.caption("이 서버에는 한글 글꼴이 없어 가운데 그림(Matplotlib)의 글자를 영어로 표시합니다.")

st.subheader("현재 선택한 데이터")
# 고른 행(view)을 표로 보입니다.
st.dataframe(view, hide_index=True, width="stretch")
# 지금 고른 데이터를 CSV로 내려받습니다. utf-8-sig는 엑셀 한글 깨짐을 막습니다.
st.download_button("현재 선택 CSV 저장", data=view.to_csv(index=False).encode("utf-8-sig"),
                   file_name="selected_sales.csv", mime="text/csv")
st.caption("이 자료만으로 실적 변화의 원인을 단정하지 않습니다.")
