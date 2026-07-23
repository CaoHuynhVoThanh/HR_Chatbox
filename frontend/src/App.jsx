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
  {
    label: 'Format CV Harvard',
    description: 'Chuẩn hoá CV tiếng Anh',
    prompt: '__FORMAT_HARVARD__',
  },
  {
    label: 'Hợp nhất CV',
    description: 'So sánh & tổng hợp 2 CV',
    prompt: '__MERGE__',
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
  const [mergeTarget, setMergeTarget] = useState(null)
  const [mergeInProgress, setMergeInProgress] = useState(false)
  const [formatInProgress, setFormatInProgress] = useState(false)
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
          { fileName: result.filename, fileData, cvText: result.text, mimeType: file.type },
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

  function startMergeFlow() {
    if (session.cvs.length < 2) {
      setError('Cần ít nhất 2 CV để hợp nhất.')
      return
    }
    // insert a special assistant message that will render merge UI
    setSession((current) => ({ ...current, messages: [...current.messages, { role: 'assistant', content: '__MERGE_INIT__' }] }))
    setMergeTarget(null)
  }

  async function confirmMerge() {
    if (mergeTarget === null) {
      setError('Vui lòng chọn CV để hợp nhất với CV chính.')
      return
    }
    setMergeInProgress(true)
    setError('')
    try {
      const primary = activeCv.cvText
      const secondaryCv = session.cvs[mergeTarget]
      const secondary = secondaryCv.cvText
      const response = await fetch(`${api}/cv/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_cv_text: primary,
          secondary_cv_text: secondary,
          primary_filename: activeCv.fileName,
          secondary_filename: secondaryCv.fileName,
        }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Không thể hợp nhất CV.')

      // append assistant markdown
      setSession((current) => ({ ...current, messages: [...current.messages, { role: 'assistant', content: result.markdown }] }))

      // prepare PDF download link from base64
      if (result.pdf_base64) {
        const bytes = Uint8Array.from(atob(result.pdf_base64), c => c.charCodeAt(0))
        const blob = new Blob([bytes], { type: 'application/pdf' })
        const url = URL.createObjectURL(blob)
        setSession((current) => ({
          ...current,
          messages: [
            ...current.messages,
            {
              role: 'assistant',
              content: 'CV theo mẫu Harvard đã sẵn sàng để tải về.',
              downloadUrl: url,
              downloadName: 'cv-harvard.pdf',
            },
          ],
        }))
      }
    } catch {
      const message = 'Chatbot chưa thể hợp nhất CV. Vui lòng thử lại trong giây lát.'
      setError(message)
      setSession((current) => ({
        ...current,
        messages: [...current.messages, { role: 'assistant', content: message }],
      }))
    } finally {
      setMergeInProgress(false)
    }
  }

  async function formatActiveCvAsHarvard() {
    if (!activeCv || formatInProgress) return
    setFormatInProgress(true)
    setError('')
    try {
      const response = await fetch(`${api}/cv/format-harvard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cv_text: activeCv.cvText, filename: activeCv.fileName }),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Không thể định dạng CV theo mẫu Harvard.')
      setSession((current) => ({
        ...current,
        messages: [
          ...current.messages,
          { role: 'assistant', content: result.markdown },
        ],
      }))
      if (result.pdf_base64) {
        const bytes = Uint8Array.from(atob(result.pdf_base64), c => c.charCodeAt(0))
        const url = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }))
        const markdownUrl = URL.createObjectURL(new Blob([result.markdown || ''], { type: 'text/markdown;charset=utf-8' }))
        setSession((current) => ({
          ...current,
          messages: [
            ...current.messages,
            {
              role: 'assistant',
              content: 'CV theo mẫu Harvard đã sẵn sàng để tải về.',
              downloadUrl: url,
              downloadName: 'cv-harvard.pdf',
              markdownDownloadUrl: markdownUrl,
              markdownDownloadName: 'cv-harvard.md',
            },
          ],
        }))
      }
    } catch (requestError) {
      const message = requestError.message || 'Chatbot chưa thể định dạng CV theo mẫu Harvard. Vui lòng thử lại trong giây lát.'
      setError(message)
      setSession((current) => ({ ...current, messages: [...current.messages, { role: 'assistant', content: message }] }))
    } finally {
      setFormatInProgress(false)
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
      let activeCvIndex = current.activeCvIndex
      if (!cvs.length) {
        activeCvIndex = 0
      } else if (index < current.activeCvIndex) {
        activeCvIndex -= 1
      } else if (index === current.activeCvIndex) {
        activeCvIndex = Math.min(index, cvs.length - 1)
      }
      return { ...current, cvs, activeCvIndex, messages: [] }
    })
    setMergeTarget(null)
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
            {session.messages.map((message, index) => {
              if (message.content === '__MERGE_INIT__') {
                return (
                  <article className={`bubble ${message.role}`} key={`merge-${index}`}>
                    <span className="bubble-label">CV INTELLIGENCE</span>
                    <div>
                      <p>Chọn 1 CV khác để hợp nhất với CV chính:</p>
                      <div className="merge-list">
                        {session.cvs.map((cv, i) => (
                          <label key={`${cv.fileName}-${i}`} className={`merge-item ${i === session.activeCvIndex ? 'disabled' : ''}`}>
                            <input
                              type="radio"
                              name="merge-target"
                              disabled={i === session.activeCvIndex}
                              checked={mergeTarget === i}
                              onChange={() => setMergeTarget(i)}
                            />
                            <img src={fileTypeIcon(cv.fileName)} alt="type" className="cv-icon" />
                            <span title={cv.fileName}>{cv.fileName}</span>
                          </label>
                        ))}
                      </div>
                      <div style={{ marginTop: 8 }}>
                        <button className="text-button" type="button" onClick={confirmMerge} disabled={mergeInProgress}>Hợp nhất</button>
                        <button className="text-button" type="button" onClick={() => {
                          // remove the merge-init message
                          setSession((current) => ({ ...current, messages: current.messages.filter((_, j) => j !== index) }))
                          setMergeTarget(null)
                        }} style={{ marginLeft: 8 }}>Hủy</button>
                      </div>
                    </div>
                  </article>
                )
              }
              if (message.downloadUrl || message.markdownDownloadUrl) {
                return (
                  <article className={`bubble ${message.role}`} key={`download-${index}`}>
                    <span className="bubble-label">CV INTELLIGENCE</span>
                    <p>{message.content}</p>
                    <div className="download-actions">
                      {message.markdownDownloadUrl && (
                        <a className="download-button secondary" href={message.markdownDownloadUrl} download={message.markdownDownloadName || 'cv-harvard.md'}>
                          ↓ Tải Markdown
                        </a>
                      )}
                      {message.downloadUrl && (
                        <a className="download-button" href={message.downloadUrl} download={message.downloadName || 'cv-harvard.pdf'}>
                          ↓ Tải PDF
                        </a>
                      )}
                    </div>
                  </article>
                )
              }
              return (
                <article className={`bubble ${message.role}`} key={`${message.role}-${index}`}>
                  <span className="bubble-label">{message.role === 'user' ? 'BẠN' : 'CV INTELLIGENCE'}</span>
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </article>
              )
            })}
            {sending && <div className="thinking"><span /><span /><span /> AI đang phân tích CV</div>}
            {mergeInProgress && <div className="thinking"><span /><span /><span /> Đang hợp nhất CV…</div>}
            {formatInProgress && <div className="thinking"><span /><span /><span /> Đang định dạng CV Harvard…</div>}
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
            {session.cvs.length > 0 && (
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
                <button className="action-button" key={action.label} type="button" disabled={!hasCv || sending || mergeInProgress || formatInProgress} onClick={() => {
                  if (action.prompt === '__MERGE__') return startMergeFlow()
                  if (action.prompt === '__FORMAT_HARVARD__') return formatActiveCvAsHarvard()
                  return sendMessage(action.prompt)
                }}>
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
