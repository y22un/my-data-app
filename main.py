import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# 1. 기본 설정
# ============================================================

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("KOBIS 영화관입장권통합전산망 일일 박스오피스")


# KOBIS 일일 박스오피스 API 주소
API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)


# ============================================================
# 2. 한국 시간 기준으로 '어제' 날짜 계산
# ============================================================

# 배포 서버가 어느 나라 시간대를 사용하든
# 한국 시간(Asia/Seoul)을 기준으로 날짜를 계산합니다.
KST = ZoneInfo("Asia/Seoul")

now_kst = datetime.now(KST)

# 오늘에서 하루를 빼면 '어제'가 됩니다.
yesterday = now_kst - timedelta(days=1)

# KOBIS API가 요구하는 날짜 형식: YYYYMMDD
target_date = yesterday.strftime("%Y%m%d")

# 화면에 보여줄 날짜 형식
display_date = yesterday.strftime("%Y년 %m월 %d일")


# ============================================================
# 3. KOBIS API에서 데이터 가져오기
# ============================================================

@st.cache_data(ttl=3600)
def get_boxoffice(target_dt):
    """
    KOBIS API에서 특정 날짜의 박스오피스 데이터를 가져옵니다.

    ttl=3600:
    같은 날짜의 API 결과를 약 1시간 동안 기억합니다.
    따라서 Streamlit 화면이 다시 실행되어도
    1시간 동안은 API를 다시 호출하지 않습니다.
    """

    # Streamlit Cloud의 Secrets에서 인증키를 가져옵니다.
    # 실제 키는 코드에 절대 적지 않습니다.
    api_key = st.secrets["KOBIS_KEY"]

    # KOBIS API에 전달할 요청값
    params = {
        "key": api_key,
        "targetDt": target_dt
    }

    try:
        # API 호출
        response = requests.get(
            API_URL,
            params=params,
            timeout=10
        )

        # HTTP 상태 코드가 정상인지 확인
        response.raise_for_status()

        # JSON 응답으로 변환
        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "message": (
                "KOBIS API 응답 시간이 초과되었습니다.\n\n"
                "잠시 후 다시 실행해 보세요. "
                "인터넷 연결이나 KOBIS 서버 상태도 확인해 주세요."
            )
        }

    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "message": (
                "KOBIS API에 접속하지 못했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결과 KOBIS API 서버 상태를 확인해 주세요."
            )
        }

    except ValueError:
        return {
            "ok": False,
            "message": (
                "KOBIS API가 올바른 JSON 데이터를 보내지 않았습니다.\n\n"
                "잠시 후 다시 시도하거나 KOBIS API 상태를 확인해 주세요."
            )
        }

    # --------------------------------------------------------
    # 인증키 오류 등을 확인
    # --------------------------------------------------------

    # KOBIS는 인증키가 잘못되어도 HTTP 상태 코드가 200일 수 있습니다.
    # 따라서 faultInfo가 있는지 반드시 확인합니다.
    if "faultInfo" in data:

        fault = data["faultInfo"]

        fault_code = fault.get("errorCode", "알 수 없음")
        fault_message = fault.get(
            "message",
            "KOBIS API에서 오류가 발생했습니다."
        )

        return {
            "ok": False,
            "message": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 코드: {fault_code}\n\n"
                f"오류 내용: {fault_message}\n\n"
                "확인할 것:\n"
                "• Streamlit Secrets에 KOBIS_KEY가 등록되어 있는지\n"
                "• 인증키를 정확하게 입력했는지\n"
                "• KOBIS API 사용 상태에 문제가 없는지"
            )
        }

    # --------------------------------------------------------
    # boxOfficeResult 확인
    # --------------------------------------------------------

    boxoffice_result = data.get("boxOfficeResult")

    if not boxoffice_result:
        return {
            "ok": False,
            "message": (
                "KOBIS API 응답에 boxOfficeResult가 없습니다.\n\n"
                "API 응답 형식이나 KOBIS 서버 상태를 확인해 주세요."
            )
        }

    # 영화 목록 가져오기
    movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "ok": False,
            "message": (
                f"{target_dt} 날짜의 박스오피스 영화 목록이 없습니다.\n\n"
                "확인할 것:\n"
                "• 조회 날짜에 영화관 집계 데이터가 존재하는지\n"
                "• KOBIS API가 정상적으로 데이터를 제공하고 있는지\n"
                "• 인증키와 API 요청 주소가 올바른지"
            )
        }

    return {
        "ok": True,
        "data": movie_list
    }


# ============================================================
# 4. API 호출
# ============================================================

result = get_boxoffice(target_date)


# ============================================================
# 5. 오류가 발생했을 때 안내
# ============================================================

if not result["ok"]:

    st.error("박스오피스 데이터를 가져오지 못했습니다.")

    # 여러 줄의 안내 문구를 그대로 보여줍니다.
    st.markdown(result["message"])

    st.info(
        "문제가 계속되면 Streamlit Cloud의 Secrets에 "
        "KOBIS_KEY가 제대로 등록되어 있는지 확인하세요."
    )

    st.stop()


# ============================================================
# 6. API 데이터를 표에 사용하기 좋은 형태로 변환
# ============================================================

movies = result["data"]

df = pd.DataFrame(movies)


# KOBIS에서 숫자가 문자열로 오기 때문에
# 정렬과 그래프에 사용할 열을 숫자로 변환합니다.
number_columns = [
    "rank",
    "audiCnt",
    "audiAcc",
    "scrnCnt",
    "showCnt"
]

for column in number_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# 순위 기준으로 정렬
df = df.sort_values("rank").reset_index(drop=True)


# ============================================================
# 7. 조회 날짜 표시
# ============================================================

st.subheader(f"📅 {display_date} 기준")

st.write(
    "아래 데이터는 KOBIS 일일 박스오피스 집계 결과입니다."
)


# ============================================================
# 8. 1위 영화 정보
# ============================================================

first_movie = df.iloc[0]

st.divider()

st.header("🏆 1위 영화")

st.subheader(
    f"🥇 {first_movie['movieNm']}"
)


# 지표 카드 세 개
col1, col2, col3 = st.columns(3)


with col1:
    st.metric(
        "어제 관객수",
        f"{int(first_movie['audiCnt']):,}명"
    )


with col2:
    st.metric(
        "누적 관객수",
        f"{int(first_movie['audiAcc']):,}명"
    )


with col3:
    st.metric(
        "스크린수",
        f"{int(first_movie['scrnCnt']):,}개"
    )


# ============================================================
# 9. 전체 영화 표
# ============================================================

st.divider()

st.header("🎞️ 전체 박스오피스")

# 화면에 보여줄 열만 선택합니다.
display_df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt"
    ]
].copy()


# 한국어 열 이름으로 변경
display_df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수"
]


# 숫자를 보기 편하게 표시하기 위한 함수
def format_number(value):
    if pd.isna(value):
        return "-"
    return f"{int(value):,}"


display_df["순위"] = display_df["순위"].apply(format_number)
display_df["관객수"] = display_df["관객수"].apply(format_number)
display_df["누적관객"] = display_df["누적관객"].apply(format_number)
display_df["스크린수"] = display_df["스크린수"].apply(format_number)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 10. 관객수 상위 5편 막대그래프
# ============================================================

st.divider()

st.header("📊 관객수 상위 5편")

# 그래프용 데이터는 숫자형을 그대로 사용합니다.
top5 = (
    df.sort_values(
        "audiCnt",
        ascending=False
    )
    .head(5)
    .copy()
)

# 영화명을 인덱스로 설정
chart_data = top5[
    ["movieNm", "audiCnt"]
].set_index("movieNm")

# Streamlit 기본 막대그래프
st.bar_chart(
    chart_data,
    y="audiCnt",
    x_label="영화",
    y_label="관객수 (명)",
    use_container_width=True
)


# ============================================================
# 11. 하단 안내
# ============================================================

st.divider()

st.caption(
    f"조회 날짜: {display_date} | "
    "조회 기준 시간대: 한국 표준시(KST)"
)

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 일일 박스오피스 API"
)

