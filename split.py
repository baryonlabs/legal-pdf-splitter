#!/usr/bin/env python3
"""
법원 제출용 PDF 분리 도구
============================
준비서면과 증거가 합쳐진 PDF를 준비서면 파일 + 증거별 개별 파일로 자동 분리합니다.

사용법:
    python split.py <PDF 파일> --brief-pages <준비서면 페이지 수>

예시:
    python split.py 준비서면_2026-05-15.pdf --brief-pages 32
    python split.py 준비서면_2026-05-15.pdf --brief-pages 32 --output-dir ./분리결과
"""

import argparse
import os
import re
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("오류: pypdf 패키지가 필요합니다.")
    print("아래 명령어로 설치하세요: pip install pypdf")
    sys.exit(1)


def 증거번호_추출(페이지_텍스트: str) -> str | None:
    """
    페이지 상단 텍스트에서 증거 번호를 추출합니다.

    인식 가능한 형식 예시:
      을 제1호증, 을제1-2호증, 을 제1호증-2, 갑제3호증 등

    반환값: '을1', '갑3' 형태의 정규화된 키 (같은 번호면 같은 파일로 묶음)
    """
    패턴 = r'([을갑])\s*제\s*(\d+)(?:[–\-](\d+))?\s*호증(?:[–\-](\d+))?'
    결과 = re.search(패턴, 페이지_텍스트[:300])
    if not 결과:
        return None

    당사자 = 결과.group(1)   # 을 또는 갑
    메인번호 = 결과.group(2)  # 기본 번호

    # 을제1-1호증, 을제1-2호증 → 모두 키 '을1' 로 묶음
    return f"{당사자}{메인번호}"


def 증거_그룹_탐지(reader: PdfReader, 시작페이지: int) -> list[tuple[str, list[int]]]:
    """
    시작페이지 이후의 페이지들을 스캔하여 같은 증거번호끼리 묶습니다.
    반환: [(증거키, [페이지인덱스, ...]), ...]
    """
    그룹목록: list[tuple[str, list[int]]] = []
    현재키 = None
    현재페이지들: list[int] = []

    for i in range(시작페이지, len(reader.pages)):
        텍스트 = reader.pages[i].extract_text() or ""
        키 = 증거번호_추출(텍스트)

        if 키 is None:
            # 증거 표기가 없으면 현재 그룹에 포함 (연속 페이지 처리)
            if 현재키 is not None:
                현재페이지들.append(i)
            else:
                그룹목록.append((f"미분류_{i+1}페이지", [i]))
        elif 키 != 현재키:
            if 현재키 is not None:
                그룹목록.append((현재키, 현재페이지들))
            현재키 = 키
            현재페이지들 = [i]
        else:
            현재페이지들.append(i)

    if 현재키 is not None and 현재페이지들:
        그룹목록.append((현재키, 현재페이지들))

    return 그룹목록


def PDF저장(reader: PdfReader, 페이지목록: list[int], 저장경로: str) -> None:
    writer = PdfWriter()
    for i in 페이지목록:
        writer.add_page(reader.pages[i])
    with open(저장경로, "wb") as f:
        writer.write(f)


def 파일명_생성(키: str) -> str:
    """'을1' → '을제1호증.pdf', '갑3' → '갑제3호증.pdf'"""
    m = re.match(r'([을갑])(\d+)', 키)
    if m:
        return f"{m.group(1)}제{m.group(2)}호증.pdf"
    return f"{키}.pdf"


def 분리실행(pdf_경로: str, 준비서면_페이지수: int, 출력폴더: str) -> None:
    os.makedirs(출력폴더, exist_ok=True)

    reader = PdfReader(pdf_경로)
    전체페이지 = len(reader.pages)

    print(f"\n파일: {os.path.basename(pdf_경로)}  (총 {전체페이지}페이지)")
    print(f"준비서면: 1~{준비서면_페이지수}페이지  |  증거: {준비서면_페이지수+1}~{전체페이지}페이지\n")
    print("-" * 50)

    # 1. 준비서면 저장
    원본명 = os.path.splitext(os.path.basename(pdf_경로))[0]
    준비서면_경로 = os.path.join(출력폴더, f"{원본명}_준비서면.pdf")
    PDF저장(reader, list(range(준비서면_페이지수)), 준비서면_경로)
    print(f"✓ 준비서면  →  {os.path.basename(준비서면_경로)}  ({준비서면_페이지수}페이지)")

    # 2. 증거 그룹 탐지 및 저장
    그룹목록 = 증거_그룹_탐지(reader, 준비서면_페이지수)

    if not 그룹목록:
        print("\n증거 페이지가 발견되지 않았습니다.")
        return

    for 키, 페이지목록 in 그룹목록:
        파일명 = 파일명_생성(키)
        저장경로 = os.path.join(출력폴더, 파일명)
        PDF저장(reader, 페이지목록, 저장경로)
        print(f"✓ {파일명:<25}  ({len(페이지목록)}페이지)")

    print("-" * 50)
    print(f"\n완료: 총 {1 + len(그룹목록)}개 파일 생성")
    print(f"저장 위치: {출력폴더}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="준비서면 + 증거 PDF를 개별 파일로 분리합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python split.py 준비서면_2026-05-15.pdf --brief-pages 32
  python split.py 준비서면_2026-05-15.pdf --brief-pages 32 --output-dir ./분리결과
        """
    )
    parser.add_argument("pdf", help="분리할 PDF 파일 경로")
    parser.add_argument(
        "--brief-pages", "-n",
        type=int,
        required=True,
        metavar="N",
        help="준비서면 페이지 수 (1페이지부터 N페이지까지가 준비서면, N+1페이지부터 증거)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        metavar="폴더",
        help="결과 파일 저장 폴더 (생략 시 원본 PDF와 같은 폴더)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"오류: 파일을 찾을 수 없습니다 → {args.pdf}")
        sys.exit(1)

    출력폴더 = args.output_dir or os.path.dirname(os.path.abspath(args.pdf))
    분리실행(args.pdf, args.brief_pages, 출력폴더)


if __name__ == "__main__":
    main()
