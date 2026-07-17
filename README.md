# HR CV Chatbot — terminal demo

Demo chatbox AI cho phép nhận xét CV, luyện phỏng vấn, đánh giá câu trả lời và tạo báo cáo. Phiên bản hiện tại **chạy tại terminal**, chưa mở FastAPI endpoint. Lõi nghiệp vụ tách riêng để có thể đưa vào client–server ở bước kế tiếp.

## Chuẩn bị

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền `GEMINI_API_KEY` vào `.env`. Gemini được gọi qua `langchain-google-genai`; model mặc định là `gemini-2.5-flash` và có thể thay bằng `GEMINI_MODEL`.

Đặt một CV `.pdf` hoặc `.docx` vào `data/cv/` (hoặc truyền đường dẫn bằng `--cv`). CV bị bỏ qua khỏi Git theo mặc định vì có dữ liệu cá nhân.

## Chạy demo

```powershell
python -m app.cli --cv data/cv/your_cv.pdf
```

Các lệnh trong chat:

- `/help` — trợ giúp
- `/report` — yêu cầu báo cáo cuối về CV/phiên phỏng vấn
- `/reload` — đọc lại CV từ ổ đĩa
- `/quit` — thoát

## Luồng agent

Mỗi lượt chat tạo một brief bao gồm năm vai trò: `Interview Planner`, `Question Generator`, `Answer Evaluator`, `Next-action Decider`, và `Final Report Generator`. Brief và CV được gửi trong một lời gọi Gemini duy nhất để hạn chế độ trễ và chi phí. Không dùng LangGraph vì luồng demo không có nhánh/trạng thái phức tạp; khi thêm nhiều vòng phỏng vấn, persistence hoặc human approval có thể thay orchestration này bằng LangGraph.

## Cấu trúc

```text
app/
  core/       # cấu hình, đọc CV, state và agent orchestration
  cli.py      # demo terminal
  server.py   # điểm tích hợp FastAPI ở giai đoạn tiếp theo (chưa có route)
data/cv/      # CV cục bộ
```

Nguồn tham khảo SDK Gemini: [Google AI for Developers](https://ai.google.dev/api/generate-content).

