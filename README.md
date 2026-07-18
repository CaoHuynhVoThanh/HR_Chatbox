# HR CV Chatbot

Chatbox AI cho phép nhận xét CV, luyện phỏng vấn, đánh giá câu trả lời và tạo báo cáo. Lõi nghiệp vụ dùng chung cho demo terminal và FastAPI backend.

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

## FastAPI backend và lưu dữ liệu

Khởi động backend:

```powershell
.\venv\Scripts\Activate.ps1
python -m app.run_server --reload
```

API chạy tại `BACKEND_PUBLIC_URL`, tài liệu tương tác tại `BACKEND_PUBLIC_URL/docs`. Có thể đổi host, port và URL public trong `.env` mà không cần sửa mã nguồn:

```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_PUBLIC_URL=https://api.example.com
```

Backend lưu dữ liệu qua lần reload/restart:

- File CV: `data/uploads/<user-id>/...`.
- SQLite: `data/hr_chatbot.db` chứa CV metadata, văn bản CV đã trích xuất, conversation và messages.

Các file này đều bị Git bỏ qua. API yêu cầu header `X-User-ID` là UUID. Frontend cần tạo một UUID một lần bằng `crypto.randomUUID()` và lưu nó ở `localStorage`; đây chỉ là định danh demo, **không phải xác thực**.

Luồng gọi API:

1. `POST /api/cv` (multipart field `file`) — upload một CV PDF/DOCX. Nếu đã có CV, gọi `POST /api/cv?replace=true` để thay thế một cách tường minh.
2. `POST /api/conversations` — tạo cuộc hội thoại cho CV hiện tại.
3. `POST /api/conversations/{conversation_id}/messages` với JSON `{"content": "..."}` — lưu tin nhắn, gọi Gemini và lưu phản hồi.
4. `GET /api/conversations/{conversation_id}/messages` — khôi phục lịch sử khi người dùng reload trang.

Ví dụ upload từ PowerShell (dùng cùng một `$userId` cho mọi request của cùng người dùng):

```powershell
$userId = [guid]::NewGuid().ToString()
$backendUrl = "http://127.0.0.1:8000" # đặt theo BACKEND_PUBLIC_URL
curl.exe -X POST "$backendUrl/api/cv" -H "X-User-ID: $userId" -F "file=@C:\duong-dan\cv.pdf"
```

## Luồng agent

Mỗi lượt chat tạo một brief bao gồm năm vai trò: `Interview Planner`, `Question Generator`, `Answer Evaluator`, `Next-action Decider`, và `Final Report Generator`. Brief và CV được gửi trong một lời gọi Gemini duy nhất để hạn chế độ trễ và chi phí. Không dùng LangGraph vì luồng demo không có nhánh/trạng thái phức tạp; khi thêm nhiều vòng phỏng vấn, persistence hoặc human approval có thể thay orchestration này bằng LangGraph.

## Cấu trúc

```text
app/
  core/       # cấu hình, đọc CV, state và agent orchestration
  cli.py      # demo terminal
  server.py   # FastAPI routes: CV, conversation, message
  core/persistence.py # SQLite repository
data/uploads/ # CV đã upload (tự tạo, bị Git ignore)
```

Nguồn tham khảo SDK Gemini: [Google AI for Developers](https://ai.google.dev/api/generate-content).
