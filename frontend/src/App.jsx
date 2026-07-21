import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import docxIcon from './images/docx_icon.svg.webp'
import pdfIcon from './images/337946.png'

const SESSION_KEY = 'hr-cv-coach-react-session-v1'
const SESSION_NOTICE_KEY = 'hr-cv-coach-session-notice-acknowledged'
const MAX_FILE_BYTES = 5 * 1024 * 1024
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const quickActions = [
  {
    label: 'Nhận xét CV',
    description: 'Điểm mạnh & khoảng trống',
    prompt: 'Hãy nhận xét CV của tôi: nêu điểm mạnh, các khoảng trống và 3 ưu tiên cải thiện.',
  },
  {
    label: 'Cải thiện CV',
    description: 'Gợi ý viết lại rõ ràng',
    prompt: 'Hãy đề xuất cách cải thiện CV của tôi, bao gồm các câu viết lại cụ thể và ưu tiên hành động.',
  },
  {
    label: '20 câu hỏi phỏng vấn',
    description: 'Bộ câu hỏi theo CV',
    prompt: 'Hãy tạo bộ đúng 20 câu hỏi phỏng vấn dựa trên CV của tôi, nhóm theo chủ đề và độ khó.',
  },
]

function emptySession() {
  return { cvs: [], activeCvIndex: 0, messages: [] }
}

function loadSession() {
  try {
    const saved = sessionStorage.getItem(SESSION_KEY)
    if (!saved) return emptySession()
    const value = JSON.parse(saved)
    if (!Array.isArray(value.messages) || !Array.isArray(value.cvs)) return emptySession()
    return { ...emptySession(), ...value }
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
    return emptySession()
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Không thể đọc tệp CV.'))
    reader.onload = () => resolve(reader.result)
    reader.readAsDataURL(file)
  })
}

function fileTypeIcon(fileName) {
  const extension = fileName.split('.').pop()?.toLowerCase()
  if (extension === 'docx') return docxIcon
  return pdfIcon
}

function toHistory(messages) {
  const history = []
  for (let index = 0; index + 1 < messages.length; index += 2) {
    const user = messages[index]
    const assistant = messages[index + 1]
    if (user.role === 'user' && assistant.role === 'assistant') {
      history.push({ user: user.content, assistant: assistant.content })
    }
  }
  return history.slice(-20)
}

function App() {
  const [session, setSession] = useState(loadSession)
  const [draft, setDraft] = useState('')
  const [uploading, setUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [showPrivacyNotice, setShowPrivacyNotice] = useState(
    () => sessionStorage.getItem(SESSION_NOTICE_KEY) !== 'true',
  )
  const fileInputRef = useRef(null)
  const messagesRef = useRef(null)

  const activeCv = session.cvs[session.activeCvIndex]
  const hasCv = Boolean(activeCv)
  const api = useMemo(() => `${API_BASE_URL}/api`, [])

  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    } catch (storageError) {
      setError('Không đủ dung lượng sessionStorage. Hãy dùng CV nhỏ hơn hoặc xóa phiên hiện tại.')
    }
  }, [session])

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'smooth' })
  }, [session.messages, sending])

  async function processCvFile(file) {
    if (!file) return
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (!['pdf', 'docx'].includes(extension)) {
      setError('Chỉ hỗ trợ CV định dạng PDF hoặc DOCX.')
      return
    }
    if (file.size > MAX_FILE_BYTES) {
      setError('CV vượt quá giới hạn 5 MB của phiên trình duyệt.')
      return
    }

    setUploading(true)
    setError('')
    try {
      const [fileData] = await Promise.all([fileToDataUrl(file)])
      const form = new FormData()
      form.append('file', file)
      const response = await fetch(`${api}/cv/extract`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Không thể xử lý CV.')

      setSession((current) => ({
        ...current,
        cvs: [
          ...current.cvs,
          { fileName: result.filename, fileData, cvText: result.text },
        ],
        activeCvIndex: current.cvs.length === 0 ? 0 : current.activeCvIndex,
        messages: [],
      }))
    } catch (requestError) {
      setError(requestError.message || 'Không thể tải CV.')
    } finally {
      setUploading(false)
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    processCvFile(file)
  }

  function selectActiveCv(index) {
    if (index === session.activeCvIndex) return
    setSession((current) => ({ ...current, activeCvIndex: index, messages: [] }))
  }

  function moveCv(index, direction) {
    const target = index + direction
    if (target < 0 || target >= session.cvs.length) return

    setSession((current) => {
      const cvs = [...current.cvs]
      const [moved] = cvs.splice(index, 1)
      cvs.splice(target, 0, moved)
      let activeCvIndex = current.activeCvIndex
      if (index === activeCvIndex) {
        activeCvIndex = target
      } else if (index < activeCvIndex && target >= activeCvIndex) {
        activeCvIndex -= 1
      } else if (index > activeCvIndex && target <= activeCvIndex) {
        activeCvIndex += 1
      }
      return { ...current, cvs, activeCvIndex }
    })
  }

  function handleDragOver(event) {
    event.preventDefault()
    if (!uploading) setIsDragging(true)
  }

  function handleDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) setIsDragging(false)
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDragging(false)
    if (!uploading) processCvFile(event.dataTransfer.files?.[0])
  }

  async function sendMessage(content) {
    const text = content.trim()
    if (!text || sending) return
    if (!hasCv) {
      setError('Hãy tải CV trước khi bắt đầu trao đổi.')
      return
    }

    const history = toHistory(session.messages)
    const userMessage = { role: 'user', content: text }
    setSession((current) => ({ ...current, messages: [...current.messages, userMessage] }))
    setDraft('')
    setSending(true)
    setError('')
    try {
      const response = await fetch(`${api}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cv_text: activeCv.cvText, history, content: text }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Không thể nhận phản hồi từ AI.')
      setSession((current) => ({
        ...current,
        messages: [...current.messages, { role: 'assistant', content: result.assistant }],
      }))
    } catch (requestError) {
      setError(requestError.message || 'Không thể gửi tin nhắn.')
    } finally {
      setSending(false)
    }
  }

  function clearSession() {
    sessionStorage.removeItem(SESSION_KEY)
    setSession(emptySession())
    setDraft('')
    setError('')
  }

  function removeCv(index) {
    setSession((current) => {
      const cvs = [...current.cvs]
      cvs.splice(index, 1)
      const activeCvIndex = Math.min(current.activeCvIndex, cvs.length - 1)
      return { ...current, cvs, activeCvIndex: activeCvIndex < 0 ? 0 : activeCvIndex, messages: cvs.length ? current.messages : [] }
    })
  }

  function acknowledgePrivacyNotice() {
    sessionStorage.setItem(SESSION_NOTICE_KEY, 'true')
    setShowPrivacyNotice(false)
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">✦</span>
          <div><strong>CV Intelligence</strong><span>AI Career Workspace</span></div>
        </div>
        {hasCv && <div className="session-status"><i className="online" />CV session active</div>}
      </header>

      <section className="workspace">
        <section className="chat-panel" aria-label="CV chat">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI CAREER ANALYST</p>
              <h1>Tối ưu CV. Chuẩn bị tự tin.</h1>
              <p>Nhận phản hồi cụ thể từ kinh nghiệm thực tế trong CV của bạn.</p>
            </div>
            <button className="text-button" type="button" onClick={clearSession}>Xóa phiên</button>
          </div>

          <div className="conversation" ref={messagesRef}>
            {!session.messages.length && (
              <div className="empty-chat">
                <span>✧</span>
                <h2>{hasCv ? 'CV đã sẵn sàng để phân tích' : 'Bắt đầu bằng việc tải CV'}</h2>
                <p>{hasCv ? 'Chọn một tác vụ bên phải hoặc đặt câu hỏi riêng.' : 'Dữ liệu chỉ nằm trong tab trình duyệt này.'}</p>
              </div>
            )}
            {session.messages.map((message, index) => (
              <article className={`bubble ${message.role}`} key={`${message.role}-${index}`}>
                <span className="bubble-label">{message.role === 'user' ? 'BẠN' : 'CV INTELLIGENCE'}</span>
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </article>
            ))}
            {sending && <div className="thinking"><span /><span /><span /> AI đang phân tích CV</div>}
          </div>

          <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(draft) }}>
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={hasCv ? 'Đặt câu hỏi về CV của bạn…' : 'Tải CV để bắt đầu…'} disabled={!hasCv || sending} />
            <button className="send-button" type="submit" disabled={!hasCv || sending || !draft.trim()} aria-label="Gửi tin nhắn">↑</button>
          </form>
          {error && <p className="error-message">{error}</p>}
        </section>

        <aside className="side-panel">
          <section className="upload-card">
            <div className="card-title"><span className="card-icon">↥</span><div><p className="eyebrow">SOURCE DOCUMENT</p><h2>CV của bạn</h2></div></div>
            <label
              className={`drop-zone ${uploading ? 'busy' : ''} ${isDragging ? 'drag-active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input ref={fileInputRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={handleFileChange} disabled={uploading} />
              <span className="upload-glyph">{uploading ? '◌' : '＋'}</span>
              <strong>{uploading ? 'Đang xử lý tài liệu…' : isDragging ? 'Thả CV vào đây' : hasCv ? 'Kéo thả để thêm CV mới' : 'Kéo thả CV vào đây'}</strong>
              <small>hoặc bấm để chọn · PDF/DOCX · tối đa 5 MB</small>
            </label>
            {session.cvs.length > 1 && (
              <div className="cv-list">
                <div className="cv-list-header">
                  <p className="cv-list-title">Nhấp vào CV để chọn làm chính</p>
                </div>
                {session.cvs.map((cv, index) => (
                  <div
                    className={`cv-item ${index === session.activeCvIndex ? 'active' : ''}`}
                    key={`${cv.fileName}-${index}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => selectActiveCv(index)}
                    onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') selectActiveCv(index) }}
                  >
                    <div className="cv-name-wrapper">
                      <img src={fileTypeIcon(cv.fileName)} alt="CV type" className="cv-icon" />
                      <span title={cv.fileName}>{cv.fileName}</span>
                    </div>
                    <div className="cv-actions">
                      {index === session.activeCvIndex && (
                        <span className="cv-active-label">CV đang dùng</span>
                      )}
                      <button className="cv-remove-button" type="button" onClick={(event) => { event.stopPropagation(); removeCv(index) }}>✕</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="actions-card">
            <div className="card-title"><span className="card-icon">⌁</span><div><p className="eyebrow">AI ACTIONS</p><h2>Các chức năng nhanh</h2></div></div>
            <div className="action-list">
              {quickActions.map((action, index) => (
                <button className="action-button" key={action.label} type="button" disabled={!hasCv || sending} onClick={() => sendMessage(action.prompt)}>
                  <span className="action-index">0{index + 1}</span>
                  <span><strong>{action.label}</strong><small>{action.description}</small></span>
                  <b>→</b>
                </button>
              ))}
            </div>
            <p className="privacy-note">Dữ liệu được giữ trong sessionStorage của tab này và bị xóa khi đóng tab.</p>
          </section>
        </aside>
      </section>

      {showPrivacyNotice && (
        <div className="privacy-modal-backdrop" role="presentation">
          <section className="privacy-modal" role="dialog" aria-modal="true" aria-labelledby="privacy-notice-title">
            <span className="privacy-modal-icon">⌁</span>
            <p className="eyebrow">QUYỀN RIÊNG TƯ PHIÊN LÀM VIỆC</p>
            <h2 id="privacy-notice-title">Dữ liệu chỉ được giữ trong tab này</h2>
            <p>CV, nội dung trích xuất và hội thoại được lưu trong sessionStorage của trình duyệt. Dữ liệu sẽ bị xóa khi bạn đóng tab và không được lưu lâu dài trên server.</p>
            <button className="confirm-button" type="button" onClick={acknowledgePrivacyNotice}>Tôi đã hiểu</button>
          </section>
        </div>
      )}
    </main>
  )
}

export default App
