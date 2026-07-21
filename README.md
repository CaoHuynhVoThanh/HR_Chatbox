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

## React frontend, FastAPI backend và dữ liệu phiên

Khởi động backend ở terminal thứ nhất:

```powershell
.\venv\Scripts\Activate.ps1
python -m app.run_server --reload
```

Khởi động React/Vite ở terminal thứ hai:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Mở `http://localhost:5173`. Giao diện desktop dùng tỉ lệ 75% chat và 25% sidebar: phần trên để upload/thay CV, phần dưới có các tác vụ Nhận xét CV, Cải thiện CV và Tạo 20 câu hỏi phỏng vấn.

API chạy tại `BACKEND_PUBLIC_URL`, tài liệu tương tác tại `BACKEND_PUBLIC_URL/docs`. Có thể đổi host, port và URL public trong `.env` mà không cần sửa mã nguồn:

```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_PUBLIC_URL=https://api.example.com
```

React client lưu toàn bộ dữ liệu ở `sessionStorage` của tab:

- File CV được mã hóa Base64, tên file và văn bản CV đã trích xuất.
- Mọi tin nhắn của phiên chat.

FastAPI **không ghi CV hoặc hội thoại vào database hay thư mục upload**. Khi cần trích xuất, CV chỉ được ghi vào file tạm rồi xóa ngay sau response. Khi reload trang trong cùng tab, client nạp lại dữ liệu từ `sessionStorage`; khi đóng tab, dữ liệu bị xóa bởi trình duyệt.

API chỉ có hai endpoint không trạng thái:

1. `POST /api/cv/extract` — nhận multipart `file`, trích xuất văn bản và không lưu file.
2. `POST /api/chat` — nhận `cv_text`, `history` và `content`; gọi Gemini rồi trả về phản hồi.

Lưu ý: `sessionStorage` không thể chứa trực tiếp đối tượng `File`, vì vậy client chuyển file sang Base64. Dung lượng mỗi tab tùy trình duyệt; client giới hạn file CV tối đa 5 MB để giảm nguy cơ vượt quota. Không dùng phương án này nếu cần giữ dữ liệu sau khi đóng tab hoặc cần đồng bộ nhiều thiết bị.

## Luồng agent

Mỗi lượt chat tạo một brief bao gồm năm vai trò: `Interview Planner`, `Question Generator`, `Answer Evaluator`, `Next-action Decider`, và `Final Report Generator`. Brief và CV được gửi trong một lời gọi Gemini duy nhất để hạn chế độ trễ và chi phí. Không dùng LangGraph vì luồng demo không có nhánh/trạng thái phức tạp; khi thêm nhiều vòng phỏng vấn, persistence hoặc human approval có thể thay orchestration này bằng LangGraph.

## Cấu trúc

```text
app/
  core/       # cấu hình, đọc CV, state và agent orchestration
  cli.py      # demo terminal
  server.py   # FastAPI stateless routes: extract CV, chat
frontend/     # React + Vite client dùng sessionStorage
```

Nguồn tham khảo SDK Gemini: [Google AI for Developers](https://ai.google.dev/api/generate-content).
