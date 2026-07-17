from __future__ import annotations

import argparse
from pathlib import Path

from app.core.chat_service import CVChatService
from app.core.config import get_settings
from app.core.cv_extractor import CVExtractionError, extract_cv, resolve_cv_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Terminal demo cho HR CV Chatbot")
    parser.add_argument("--cv", help="Đường dẫn CV .pdf hoặc .docx. Mặc định: file duy nhất trong data/cv/")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        path = resolve_cv_path(args.cv)
        cv = extract_cv(path)
        service = CVChatService(get_settings(), cv)
    except (CVExtractionError, RuntimeError) as exc:
        raise SystemExit(f"Lỗi khởi tạo: {exc}") from exc

    print(f"Đã nạp CV: {Path(cv.path).name} ({len(cv.text):,} ký tự).")
    print("HR CV Coach sẵn sàng. Gõ /help để xem lệnh.")
    while True:
        try:
            message = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nĐã kết thúc phiên chat.")
            return
        if message in {"/quit", "/exit"}:
            print("Tạm biệt!")
            return
        if message == "/help":
            print("/report: báo cáo cuối | /reload: nạp lại CV | /quit: thoát")
            continue
        if message == "/reload":
            try:
                service.session.cv = extract_cv(service.session.cv.path)
                print("Đã nạp lại CV.")
            except CVExtractionError as exc:
                print(f"Không thể nạp lại CV: {exc}")
            continue
        if message == "/report":
            message = "Hãy tạo báo cáo tổng kết về CV và phiên luyện phỏng vấn đến hiện tại."
        try:
            print(f"\nHR CV Coach: {service.reply(message)}")
        except Exception as exc:
            print(f"Không thể gọi Gemini: {exc}")


if __name__ == "__main__":
    main()

