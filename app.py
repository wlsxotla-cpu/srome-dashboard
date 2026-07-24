"""
KEIT SROME 수요조사·인터넷공시 대시보드 (Streamlit)

GitHub의 wlsxotla-cpu/iris-monitor-v2 리포지토리에서 GitHub Actions가
만들어두는 results/srome.json 을 읽어서 카드 형태로 보여준다.
IRIS 대시보드와는 완전히 별도의 앱이다 (가끔만 확인하는 용도라 분리함).
"""

import time
from datetime import datetime, timedelta, timezone

import requests
import streamlit as st

SROME_JSON_URL = (
    "https://raw.githubusercontent.com/wlsxotla-cpu/iris-monitor-v2/main/results/srome.json"
)

SROME_LIST_URLS = {
    "수요조사": "https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveDmndSrvyLstView.do?prgmId=XPG201010000",
    "인터넷공시": "https://srome.keit.re.kr/srome/biz/perform/opnnPrpsl/retrieveIntrnDsclsLstView.do?prgmId=XPG201020000",
}


def _html(s: str) -> str:
    """각 줄의 앞뒤 공백을 제거해서, 마크다운이 들여쓰기를 코드블럭으로
    오인하지 않도록 한다."""
    return "\n".join(line.strip() for line in s.strip("\n").split("\n"))


GH_REPO = "wlsxotla-cpu/iris-monitor-v2"
GH_WORKFLOW_FILE = "scrape.yml"


def trigger_scrape():
    token = st.secrets.get("GITHUB_TOKEN")
    if not token:
        return False, "GITHUB_TOKEN이 설정되어 있지 않습니다 (앱 Settings > Secrets에서 추가해주세요)."
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW_FILE}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"ref": "main"},
            timeout=15,
        )
    except Exception as e:
        return False, str(e)

    if resp.status_code == 204:
        return True, None
    return False, f"{resp.status_code}: {resp.text[:200]}"


def get_latest_run(token, since_iso):
    """방금 트리거한 실행을 찾는다 (since_iso 이후 생성된 것 중 가장 오래된 = 방금 만든 것)."""
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW_FILE}/runs"
    try:
        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"event": "workflow_dispatch", "per_page": 5},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception:
        return None

    runs = resp.json().get("workflow_runs", [])
    candidates = [r for r in runs if r["created_at"] >= since_iso]
    if candidates:
        return candidates[-1]
    return None


st.set_page_config(page_title="SROME 수요조사·인터넷공시", layout="wide")

st.markdown(
    _html(
        """
        <style>
        .ancm-card {
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 10px;
        }
        .ancm-title { font-weight: 600; margin-bottom: 4px; }
        .ancm-meta { color: #777; font-size: 0.85rem; margin-bottom: 8px; }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 4px;
        }
        .badge-status { background: #e6f6ec; color: #14803c; }
        .badge-period { background: #fff4e0; color: #a15c00; }
        .badge-dday { background: #fdecea; color: #c0392b; }
        .tag-new {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 4px;
            background: #ffe8e8;
            color: #c0392b;
        }
        </style>
        """
    ),
    unsafe_allow_html=True,
)

def update_badge_html(updated_at_str: str) -> str:
    KST = timezone(timedelta(hours=9))
    try:
        dt = datetime.strptime(updated_at_str.replace(" KST", ""), "%Y-%m-%d %H:%M")
        today = datetime.now(KST).replace(tzinfo=None).date()
        is_today = dt.date() == today
        bg, color = ("#e6f6ec", "#14803c") if is_today else ("#fdecea", "#c0392b")
        label = "🟢 오늘 갱신됨" if is_today else "🔴 갱신이 늦어지고 있어요"
    except Exception:
        bg, color, label = "#eee", "#555", "ℹ️"

    return (
        f'<div style="display:inline-block;background:{bg};color:{color};'
        f'padding:6px 16px;border-radius:999px;font-weight:700;font-size:0.95rem;'
        f'margin-bottom:12px;">{label} · 마지막 갱신 {updated_at_str}</div>'
    )


def is_new(notice_date_str: str, days: int = 7) -> bool:
    KST = timezone(timedelta(hours=9))
    try:
        d = datetime.strptime(notice_date_str, "%Y-%m-%d").date()
        today = datetime.now(KST).replace(tzinfo=None).date()
        return (today - d).days <= days
    except Exception:
        return False


st.title("🔎 SROME 수요조사·인터넷공시")
st.caption("⏰ IRIS 스크래퍼와 같은 GitHub Actions에서 매일 새벽 6시경(KST)에 같이 갱신됩니다.")


@st.cache_data(ttl=300)
def load_data():
    resp = requests.get(SROME_JSON_URL, timeout=15)
    resp.raise_for_status()
    return resp.json()


try:
    data = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.stop()

st.markdown(update_badge_html(data.get("updated_at", "")), unsafe_allow_html=True)
st.markdown(
    _html(
        """
        <div style="display:inline-block;background:#ffe8e8;color:#c0392b;
        padding:6px 16px;border-radius:999px;font-weight:700;font-size:0.95rem;
        margin-bottom:12px;">⭐ NEW = 공고일 기준 최근 7일 이내 등록된 항목</div>
        """
    ),
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ 설정")
    st.caption(f"마지막 갱신: {data.get('updated_at', '알 수 없음')}")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

    if st.button("🚀 지금 수집"):
        since = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ok, err = trigger_scrape()
        if not ok:
            st.error(err)
        else:
            token = st.secrets.get("GITHUB_TOKEN")
            with st.status("수집 요청을 보냈습니다...", expanded=True) as status:
                time.sleep(5)
                run = None
                for attempt in range(30):
                    run = get_latest_run(token, since)
                    if run and run["status"] == "completed":
                        break
                    status.write(f"진행 중... ({run['status'] if run else '실행 확인 중'})")
                    time.sleep(5)

                if run and run["status"] == "completed":
                    if run["conclusion"] == "success":
                        status.update(label="✅ 수집 완료! 목록을 새로고침합니다.", state="complete")
                        st.cache_data.clear()
                    else:
                        status.update(
                            label=f"❌ 수집 실패 ({run['conclusion']}) - Actions 로그를 확인해주세요",
                            state="error",
                        )
                else:
                    status.update(
                        label="⏱️ 시간이 오래 걸리고 있습니다 - Actions 탭에서 직접 확인해주세요",
                        state="error",
                    )
            st.rerun()

items = data.get("items", [])

for category, list_url in SROME_LIST_URLS.items():
    cat_items = [i for i in items if i.get("category") == category]
    st.subheader(f"{category} ({len(cat_items)}건)")

    if not cat_items:
        st.caption("아직 준비 중이거나 현재 조회된 항목이 없습니다.")
        st.link_button(f"{category} 사이트에서 직접 보기 ↗", list_url)
        continue

    cols = st.columns(3)
    for i, item in enumerate(cat_items):
        with cols[i % 3]:
            detail_url = item.get("detail_url")
            link_html = (
                f'<a href="{detail_url}" target="_blank" style="'
                'display:inline-block;padding:4px 10px;border-radius:6px;'
                'border:1px solid #2c5aa0;background:white;color:#2c5aa0;'
                'text-decoration:none;font-size:0.85rem;">'
                "🔗 SROME에서 보기</a>"
                if detail_url
                else ""
            )
            new_badge = '<span class="tag-new">⭐ NEW</span>' if is_new(item.get("notice_date", "")) else ""
            st.markdown(
                _html(
                    f"""
                    <div class="ancm-card">
                    <div class="ancm-title">{new_badge}{item['title']}</div>
                    <div class="ancm-meta">
                    <span class="badge badge-status">{item.get('status', '')}</span>
                    <span class="badge badge-dday">{item.get('dday', '')}</span><br><br>
                    기획년도 {item.get('plan_year', '')}<br>
                    <span class="badge badge-period">접수기간 {item.get('period', '')}</span><br><br>
                    공고일 {item.get('notice_date', '')}<br>
                    {link_html}
                    </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
    st.link_button(f"{category} 전체 목록 사이트에서 보기 ↗", list_url)

st.divider()
st.caption("KOTERI SJT")
