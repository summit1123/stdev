import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import './App.css'

function inferHostedApiBase(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  const { protocol, hostname } = window.location
  if (hostname === 'diary-app.summit1123.co.kr') {
    return `${protocol}//diary-api.summit1123.co.kr`
  }
  if (hostname === 'app.summit1123.co.kr') {
    return `${protocol}//api.summit1123.co.kr`
  }
  return null
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? inferHostedApiBase() ?? 'http://localhost:8000'
const BRAND_NAME = 'kwail'
const BRAND_LOGO = '/branding/kwail-lemon-bulb-mark.png'

type EntryStatus =
  | 'created'
  | 'text_ready'
  | 'queued'
  | 'parsing'
  | 'planning'
  | 'rendering_image'
  | 'rendering_audio'
  | 'rendering_video'
  | 'completed'
  | 'failed'

type InputType = 'image' | 'voice'
type ModeId = 'observe' | 'experiment' | 'imagine'

type EntryListItem = {
  entryId: string
  createdAt: string
  status: EntryStatus
  summary?: string | null
  emotions: string[]
  posterUrl?: string | null
  missionLogCount: number
}

type EntryStatusResponse = {
  entryId: string
  status: EntryStatus
  preferredModeId: ModeId
  originalFileUrl?: string | null
  rawText: string
  normalizedText: string
  parseWarnings: string[]
  errorMessage?: string | null
  hasResult: boolean
  missionLogCount: number
}

type GameModeCard = {
  id: ModeId
  title: string
  hook: string
  mission: string
  reward: string
}

type VideoShot = {
  sceneTitle: string
  subtitle: string
  visualPrompt: string
  durationSeconds: number
}

type SceneVisual = {
  title: string
  prompt: string
  caption: string
  imageUrl?: string | null
}

type ScienceGame = {
  title: string
  premise: string
  goal: string
  howToPlay: string[]
  winCondition: string
  aiGuide: string
}

type ScienceQuiz = {
  title: string
  question: string
  options: string[]
  answerIndex: number
  explanation: string
}

type ScientificInterpretation = {
  title: string
  observation: string
  concept: string
  explanation: string
  measurementIdea: string
  safetyNote: string
}

type EntryResult = {
  entryId: string
  summary: string
  emotions: string[]
  scienceLens: string[]
  questionSeeds: string[]
  scientificInterpretation: ScientificInterpretation
  sceneVisual: SceneVisual
  scienceGame: ScienceGame
  scienceQuiz: ScienceQuiz
  gameModes: GameModeCard[]
  recommendedModeId: ModeId
  experimentCard: {
    title: string
    hypothesis: string
    independentVariable: string
    dependentVariable: string
    method: string
    durationDays: number
    whatToWatch: string
  }
  videoDirector: {
    title: string
    concept: string
    visualStyle: string
    mixDirection: string
    scenarioText: string
    soraPrompt: string
    targetDurationSeconds: number
    shots: VideoShot[]
  }
  creativeExpansion?: {
    type: 'story' | 'alternate_world' | 'character'
    text: string
  } | null
  guardianNote?: string | null
  narration: {
    script: string
    audioUrl?: string | null
    voice?: string | null
    durationSec?: number | null
  }
  sceneCards: Array<{ title: string; body: string }>
  media: {
    posterUrl?: string | null
    videoUrl?: string | null
    videoModel?: string | null
    thumbnailUrl?: string | null
    soraRequestUrl?: string | null
    soraVideoUrl?: string | null
    storyboardUrls: string[]
    generatedStoryboardUrls: string[]
  }
  analysisMode: 'openai' | 'fallback'
}

type MissionLog = {
  id: string
  observationData: string
  reflection: string
  createdAt: string
}

type CardChatKind = 'summary' | 'question' | 'experiment' | 'interpretation'

type CardChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

type CardChatModalState = {
  kind: CardChatKind
  cardTitle: string
  cardBody: string
}

type AppView = 'home' | 'studio'
type StudioPage = 'source' | 'ocr' | 'results' | 'library'

const homeJourneySteps = [
  {
    title: '읽기',
    body: '손글씨를 그대로 읽고, 제목과 본문을 나눠서 바로 확인합니다.',
  },
  {
    title: '질문 만들기',
    body: '정답을 채점하지 않고, 오늘의 장면을 질문 3개 안으로 압축합니다.',
  },
  {
    title: '실험 연결',
    body: '내일 다시 돌아오게 만드는 관찰 미션과 기록 포인트를 붙입니다.',
  },
  {
    title: '설명 듣기',
    body: '상황 이미지와 24초 과학 해석 영상을 같은 흐름으로 묶습니다.',
  },
]

const homeModes = [
  {
    title: '탐정 모드',
    body: '일기 속 어떤 장면에서든 "왜 그랬을까?"를 질문 삼아 과학 원리를 추리합니다.',
  },
  {
    title: '발명가 모드',
    body: '일기 속 어떤 장면에서든 숨어있는 과학 원리를 꺼내 새로운 아이디어로 연결합니다.',
  },
  {
    title: '탐험가 모드',
    body: '일기 속 어떤 순간이든 처음 발견한 것처럼 낯설게 바라보며 과학을 찾아냅니다.',
  },
]

const modeOrder: ModeId[] = ['observe', 'experiment', 'imagine']

const statusMeta: Record<EntryStatus, { label: string; detail: string; progress: number }> = {
  created: {
    label: '파일을 올려 주세요',
    detail: '일기 이미지를 올리면 바로 읽은 글로 정리하고, 다음 단계에서 다듬을 수 있습니다.',
    progress: 0,
  },
  text_ready: {
    label: '텍스트 확인 단계',
    detail: '잘못 읽힌 부분만 고치면 바로 생성할 수 있습니다.',
    progress: 18,
  },
  queued: {
    label: '생각을 정리하는 중이에요',
    detail: '서버에서 작업을 잡았고, 지금부터 흐름에 맞춰 차례대로 준비합니다.',
    progress: 28,
  },
  parsing: {
    label: '손글씨를 살펴보는 중이에요',
    detail: '손글씨와 장면 단서를 다시 읽고 있습니다.',
    progress: 42,
  },
  planning: {
    label: '질문을 고르는 중이에요',
    detail: '질문, 게임, 설명, 영상 시나리오를 함께 짜고 있습니다.',
    progress: 58,
  },
  rendering_image: {
    label: '장면을 그려 보는 중이에요',
    detail: '일기 속 장면을 한 컷의 일러스트로 재구성하고 있습니다.',
    progress: 72,
  },
  rendering_audio: {
    label: '설명을 다듬는 중이에요',
    detail: '영상과 결과 카드를 맞추기 위해 최종 설명을 정리하고 있습니다.',
    progress: 82,
  },
  rendering_video: {
    label: '영상과 목소리를 맞추는 중이에요',
    detail: '장면 카드 영상과 내레이션을 합쳐 최종 결과를 정리하고 있습니다.',
    progress: 92,
  },
  completed: {
    label: '생성 완료',
    detail: '이미지, 과학 게임, 과학 해석 영상까지 모두 준비됐습니다.',
    progress: 100,
  },
  failed: {
    label: '다시 시도 필요',
    detail: '생성 중 문제가 생겨서 다시 실행할 수 있는 상태입니다.',
    progress: 0,
  },
}

const pipelineSteps = [
  { key: 'upload', label: '업로드' },
  { key: 'ocr', label: '읽기 확인' },
  { key: 'plan', label: '과학 설계' },
  { key: 'image', label: '상황 이미지' },
  { key: 'video', label: '영상 믹싱' },
]

const modeCopy: Record<ModeId, GameModeCard> = {
  observe: {
    id: 'observe',
    title: '탐정 모드',
    hook: '일기 속 어떤 장면에서든 "왜 그랬을까?"를 질문 삼아 과학 원리를 추리하는 모드',
    mission: '일기의 행동, 감각, 변화 중 하나를 골라 원인을 추적하는 단서에서 추리로 이어지는 흐름으로 구성합니다.',
    reward: '시나리오와 이미지, 영상도 단서와 원인 추리 흐름으로 이어집니다.',
  },
  experiment: {
    id: 'experiment',
    title: '발명가 모드',
    hook: '일기 속 어떤 장면에서든 숨어있는 과학 원리를 꺼내 새로운 아이디어로 연결하는 모드',
    mission: '일기의 사물, 행동, 현상 중 하나를 골라 원리를 설명한 뒤 "이걸 응용하면?"으로 이어지는 흐름으로 구성합니다.',
    reward: '시나리오와 이미지, 영상도 원리 설명 뒤 응용 아이디어로 확장합니다.',
  },
  imagine: {
    id: 'imagine',
    title: '탐험가 모드',
    hook: '일기 속 어떤 순간이든 처음 발견한 것처럼 낯설게 바라보며 과학을 찾아내는 모드',
    mission: '일기에서 당연하게 지나친 장면을 골라 "이게 왜 당연한 걸까?"라는 탐험 질문으로 바꿔 구성합니다.',
    reward: '시나리오와 이미지, 영상도 낯설게 다시 보는 탐험 흐름으로 이어집니다.',
  },
}

const studioPages: Array<{ id: StudioPage; step: string; title: string; blurb: string }> = [
  { id: 'source', step: '1', title: '업로드', blurb: '일기 파일을 올리고 샘플을 고릅니다.' },
  { id: 'ocr', step: '2', title: '읽기 확인', blurb: '읽힌 문장을 다듬고 어떤 방식으로 탐구할지 정합니다.' },
  { id: 'results', step: '3', title: '결과 보기', blurb: '과학 해석, 이미지, 영상을 확인합니다.' },
  { id: 'library', step: '4', title: '보관함', blurb: '이전 세션을 다시 열고 이어서 봅니다.' },
]

const busyStatuses = new Set<EntryStatus>([
  'queued',
  'parsing',
  'planning',
  'rendering_image',
  'rendering_audio',
  'rendering_video',
])

const resultCardKinds: CardChatKind[] = ['summary', 'question', 'experiment', 'interpretation']

const cardChatMeta: Record<
  CardChatKind,
  {
    title: string
    helper: string
    opening: string
    prompts: string[]
  }
> = {
  summary: {
    title: '현상 요약 더 묻기',
    helper: '오늘 장면을 어떤 과학 현상으로 읽을지 더 짚어봅니다.',
    opening: '이 카드에서는 오늘 장면을 과학 현상으로 다시 읽는 데 필요한 단서를 같이 고를 수 있어요.',
    prompts: ['이 장면에서 가장 먼저 봐야 할 변수는 뭐야?', '오늘 장면을 한 문장 과학 질문으로 바꾸면?', '비교해서 보면 좋은 단서는 뭐야?'],
  },
  question: {
    title: '질문 씨앗 다듬기',
    helper: '질문을 더 또렷하고 관찰 가능하게 바꿉니다.',
    opening: '이 카드에서는 막연한 궁금증을 비교하고 기록할 수 있는 질문으로 다듬어 볼 수 있어요.',
    prompts: ['이 질문을 더 또렷하게 바꾸면?', '무엇을 바꾸고 무엇을 기록하면 돼?', '같이 비교하면 좋은 조건은 뭐야?'],
  },
  experiment: {
    title: '미니 실험 이어 묻기',
    helper: '실제로 바로 해볼 수 있는 안전한 실험 흐름으로 이어집니다.',
    opening: '이 카드에서는 집이나 교실에서 바로 해볼 수 있게 실험 순서를 더 짧고 분명하게 풀어줄게요.',
    prompts: ['준비물은 최소로 어떻게 할 수 있어?', '한 번에 하나만 바꾸려면 뭘 고정해야 해?', '기록표는 어떻게 적으면 좋아?'],
  },
  interpretation: {
    title: 'AI 해설 더 쉽게 듣기',
    helper: '어려운 과학 말을 쉬운 말로 다시 설명합니다.',
    opening: '이 카드에서는 과학 해설을 쉬운 말로 다시 풀고, 무엇을 다시 보면 좋은지도 같이 알려줄 수 있어요.',
    prompts: ['이걸 초등학생 말로 다시 설명해줘', '왜 이런 차이가 생긴다고 볼 수 있어?', '눈으로 확인할 수 있는 단서는 뭐야?'],
  },
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'request failed' }))
    throw new Error(error.detail ?? 'request failed')
  }
  return response.json() as Promise<T>
}

function resolveMediaUrl(url?: string | null): string | null {
  if (!url) {
    return null
  }
  if (/^(https?:|blob:|data:)/.test(url)) {
    return url
  }
  return `${API_BASE}${url}`
}

function withAssetVersion(url: string | null, version: number): string | null {
  if (!url) {
    return null
  }
  if (/^(blob:|data:)/.test(url)) {
    return url
  }
  return `${url}${url.includes('?') ? '&' : '?'}v=${version}`
}

function mediaSignature(result?: EntryResult | null): string {
  if (!result) {
    return ''
  }
  return JSON.stringify({
    videoUrl: result.media.videoUrl ?? '',
    thumbnailUrl: result.media.thumbnailUrl ?? '',
    sceneImageUrl: result.sceneVisual.imageUrl ?? '',
    storyboardUrls: result.media.storyboardUrls ?? [],
    generatedStoryboardUrls: result.media.generatedStoryboardUrls ?? [],
    duration: result.videoDirector.targetDurationSeconds ?? 0,
  })
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('ko-KR', {
    month: 'numeric',
    day: 'numeric',
  })
}

function getDiaryExcerpt(text: string, limit = 170): string {
  const compact = text.replace(/\s+/g, ' ').trim()
  if (!compact) {
    return ''
  }
  return compact.length <= limit ? compact : `${compact.slice(0, limit).trimEnd()}...`
}

function getStudioPageFromHash(): StudioPage {
  const hash = window.location.hash
  if (hash.startsWith('#/studio/')) {
    const page = hash.replace('#/studio/', '')
    if (page === 'source' || page === 'ocr' || page === 'results' || page === 'library') {
      return page
    }
  }
  return 'source'
}

function getInitialView(): AppView {
  return window.location.hash.startsWith('#/studio') ? 'studio' : 'home'
}

function getStudioPageFromState(status: EntryStatus, hasResult: boolean): StudioPage {
  if (hasResult || busyStatuses.has(status)) {
    return 'results'
  }
  if (status === 'text_ready') {
    return 'ocr'
  }
  return 'source'
}

function App() {
  const [view, setView] = useState<AppView>(getInitialView)
  const [entries, setEntries] = useState<EntryListItem[]>([])
  const [preferredModeId, setPreferredModeId] = useState<ModeId>('observe')
  const [currentEntryId, setCurrentEntryId] = useState<string | null>(null)
  const [entryStatus, setEntryStatus] = useState<EntryStatusResponse | null>(null)
  const [result, setResult] = useState<EntryResult | null>(null)
  const [missionLogs, setMissionLogs] = useState<MissionLog[]>([])
  const [transcript, setTranscript] = useState('')
  const [uploadPreview, setUploadPreview] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [assetVersion, setAssetVersion] = useState(() => Date.now())
  const mediaSignatureRef = useRef('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const previewUrlRef = useRef<string | null>(null)
  const [missionDraft, setMissionDraft] = useState({ observationData: '', reflection: '' })
  const [quizChoice, setQuizChoice] = useState<number | null>(null)
  const [quizSubmitted, setQuizSubmitted] = useState(false)
  const [gameStepIndex, setGameStepIndex] = useState(0)
  const [activeCardChat, setActiveCardChat] = useState<CardChatModalState | null>(null)
  const [cardChatHistory, setCardChatHistory] = useState<CardChatMessage[]>([])
  const [cardChatInput, setCardChatInput] = useState('')
  const [isCardChatLoading, setIsCardChatLoading] = useState(false)
  const [videoLoadError, setVideoLoadError] = useState(false)
  const [message, setMessage] = useState('일기의 장면을 과학 질문, 게임, 영상으로 연결할 준비가 됐어요.')
  const [error, setError] = useState<string | null>(null)
  const [activeStudioPage, setActiveStudioPage] = useState<StudioPage>(getStudioPageFromHash)

  const currentStatus = entryStatus?.status ?? 'created'
  const currentMeta = statusMeta[currentStatus]
  const isBusy = isUploading || isAnalyzing || busyStatuses.has(currentStatus)
  const latestEntry = entries[0] ?? null
  const currentStudioPage = activeStudioPage === 'results' && !result && !isBusy && currentStatus === 'created'
    ? 'source'
    : activeStudioPage

  const currentPoster = useMemo(
    () =>
      withAssetVersion(
        resolveMediaUrl(uploadPreview || result?.media.posterUrl || entryStatus?.originalFileUrl || null),
        assetVersion,
      ),
    [assetVersion, entryStatus?.originalFileUrl, result?.media.posterUrl, uploadPreview],
  )

  const sceneVisualUrl = useMemo(
    () => withAssetVersion(resolveMediaUrl(result?.sceneVisual.imageUrl), assetVersion),
    [assetVersion, result?.sceneVisual.imageUrl],
  )

  const generatedStoryboardUrls = useMemo(
    () => (result?.media.generatedStoryboardUrls ?? []).map((url) => withAssetVersion(resolveMediaUrl(url), assetVersion)).filter(Boolean) as string[],
    [assetVersion, result?.media.generatedStoryboardUrls],
  )

  const localVideoUrl = useMemo(
    () => withAssetVersion(resolveMediaUrl(result?.media.videoUrl), assetVersion),
    [assetVersion, result?.media.videoUrl],
  )
  const thumbnailUrl = useMemo(
    () => withAssetVersion(resolveMediaUrl(result?.media.thumbnailUrl), assetVersion),
    [assetVersion, result?.media.thumbnailUrl],
  )
  const videoPreviewImage = thumbnailUrl || generatedStoryboardUrls[0] || sceneVisualUrl
  const videoDurationLabel = `${result?.videoDirector.targetDurationSeconds ?? 24}초`
  const diaryExcerpt = useMemo(
    () => getDiaryExcerpt(transcript || entryStatus?.normalizedText || entryStatus?.rawText || ''),
    [entryStatus?.normalizedText, entryStatus?.rawText, transcript],
  )

  const sortedModes = useMemo(() => {
    if (!result || !result.gameModes.length) {
      return modeOrder.map((id) => modeCopy[id])
    }
    const generated = new Map(result.gameModes.map((mode) => [mode.id, mode]))
    return modeOrder
      .map((id) => ({ ...generated.get(id), ...modeCopy[id] }))
      .sort((a, b) => (a.id === result.recommendedModeId ? -1 : b.id === result.recommendedModeId ? 1 : 0))
  }, [result])
  async function refreshEntries() {
    const list = await api<EntryListItem[]>('/api/v1/entries')
    setEntries(list)
  }

  useEffect(() => {
    void refreshEntries()
  }, [])

  useEffect(() => {
    const onHashChange = () => {
      setView(getInitialView())
      setActiveStudioPage(getStudioPageFromHash())
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    setQuizChoice(null)
    setQuizSubmitted(false)
    setGameStepIndex(0)
    setActiveCardChat(null)
    setCardChatHistory([])
    setCardChatInput('')
    setIsCardChatLoading(false)
  }, [result?.entryId])

  useEffect(() => {
    if (!activeCardChat) {
      return
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setActiveCardChat(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [activeCardChat])

  useEffect(() => {
    setVideoLoadError(false)
  }, [localVideoUrl])

  useEffect(() => {
    const signature = mediaSignature(result)
    if (signature) {
      mediaSignatureRef.current = signature
    }
  }, [result])

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!currentEntryId || !entryStatus) {
      return
    }

    if (!busyStatuses.has(entryStatus.status)) {
      return
    }

    const timer = window.setInterval(async () => {
      try {
        const nextStatus = await api<EntryStatusResponse>(`/api/v1/entries/${currentEntryId}`)
        setEntryStatus(nextStatus)
        if (nextStatus.hasResult) {
          const nextResult = await api<EntryResult>(`/api/v1/entries/${currentEntryId}/result`)
          const nextSignature = mediaSignature(nextResult)
          if (nextSignature && nextSignature !== mediaSignatureRef.current) {
            mediaSignatureRef.current = nextSignature
            setAssetVersion(Date.now())
          }
          setResult(nextResult)
          setMissionLogs(await api<MissionLog[]>(`/api/v1/entries/${currentEntryId}/mission-log`))
          setPreferredModeId(nextResult.recommendedModeId)
          if (nextStatus.status === 'completed') {
            setMessage(`이미지, 과학 게임, ${nextResult.videoDirector.targetDurationSeconds}초 영상이 모두 준비됐어요.`)
            setIsAnalyzing(false)
          } else {
            setMessage('중간 결과를 먼저 보여주고 있어요. 영상 렌더링은 계속 진행됩니다.')
          }
          await refreshEntries()
        }

        if (nextStatus.status === 'failed') {
          setIsAnalyzing(false)
        }
      } catch (pollError) {
        setError(pollError instanceof Error ? pollError.message : '상태를 불러오지 못했어요.')
      }
    }, 1800)

    return () => window.clearInterval(timer)
  }, [currentEntryId, entryStatus])

  async function loadEntry(entryId: string) {
    navigateToView('studio')
    setCurrentEntryId(entryId)
    setError(null)
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
    const nextStatus = await api<EntryStatusResponse>(`/api/v1/entries/${entryId}`)
    setEntryStatus(nextStatus)
    setPreferredModeId(nextStatus.preferredModeId)
    setTranscript(nextStatus.normalizedText)
    setUploadPreview(nextStatus.originalFileUrl ?? null)
    if (nextStatus.hasResult || nextStatus.status === 'completed') {
      const nextResult = await api<EntryResult>(`/api/v1/entries/${entryId}/result`)
      const nextSignature = mediaSignature(nextResult)
      if (nextSignature) {
        mediaSignatureRef.current = nextSignature
        setAssetVersion(Date.now())
      }
      setResult(nextResult)
      setPreferredModeId(nextResult.recommendedModeId)
      navigateToStudioPage('results')
    } else {
      setResult(null)
      navigateToStudioPage(getStudioPageFromState(nextStatus.status, nextStatus.hasResult))
    }
    setMissionLogs(await api<MissionLog[]>(`/api/v1/entries/${entryId}/mission-log`))
  }

  async function uploadFile(file: File, inputType: InputType) {
    navigateToView('studio')
    setIsUploading(true)
    setError(null)
    setResult(null)
    setMissionLogs([])

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
    if (file.type.startsWith('image/')) {
      const localPreview = URL.createObjectURL(file)
      previewUrlRef.current = localPreview
      setUploadPreview(localPreview)
    } else {
      setUploadPreview(null)
    }

    try {
      const created = await api<{ entryId: string; status: EntryStatus }>('/api/v1/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputType }),
      })

      setCurrentEntryId(created.entryId)

      const form = new FormData()
      form.append('file', file)
      const uploaded = await api<{
        entryId: string
        status: EntryStatus
        rawText: string
        normalizedText: string
        parseWarnings: string[]
        originalFileUrl: string
      }>(`/api/v1/entries/${created.entryId}/upload`, {
        method: 'POST',
        body: form,
      })

      setTranscript(uploaded.normalizedText)
      setEntryStatus({
        entryId: uploaded.entryId,
        status: uploaded.status,
        preferredModeId,
        originalFileUrl: uploaded.originalFileUrl,
        rawText: uploaded.rawText,
        normalizedText: uploaded.normalizedText,
        parseWarnings: uploaded.parseWarnings,
        hasResult: false,
        missionLogCount: 0,
      })
      setMessage('읽힌 문장을 다듬고 모드를 고르면 바로 결과를 만들 수 있어요.')
      navigateToStudioPage('ocr')
      await refreshEntries()
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : '업로드에 실패했어요.')
    } finally {
      setIsUploading(false)
    }
  }

  async function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    const type: InputType = 'image'
    await uploadFile(file, type)
    event.target.value = ''
  }

  async function onFileDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    const file = event.dataTransfer.files?.[0]
    if (!file) {
      return
    }
    await uploadFile(file, 'image')
  }

  function openFilePicker() {
    fileInputRef.current?.click()
  }

  async function onAnalyzeRequest() {
    if (!currentEntryId || !transcript.trim()) {
      return
    }

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const response = await api<{ entryId: string; jobId: string; status: EntryStatus }>(
        `/api/v1/entries/${currentEntryId}/analyze`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ normalizedText: transcript, preferredModeId }),
        },
      )

      setEntryStatus((prev) =>
        prev
          ? {
              ...prev,
              status: response.status,
              normalizedText: transcript,
              preferredModeId,
            }
          : null,
      )
      setMessage('지금은 과학 질문, 장면 이미지, 24초 영상을 순서대로 만들고 있어요.')
      navigateToStudioPage('results')
    } catch (analyzeError) {
      setIsAnalyzing(false)
      setError(analyzeError instanceof Error ? analyzeError.message : '분석에 실패했어요.')
    }
  }

  async function onSaveMission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!currentEntryId || !missionDraft.observationData.trim() || !missionDraft.reflection.trim()) {
      return
    }

    try {
      await api(`/api/v1/entries/${currentEntryId}/mission-log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(missionDraft),
      })
      setMissionDraft({ observationData: '', reflection: '' })
      setMissionLogs(await api<MissionLog[]>(`/api/v1/entries/${currentEntryId}/mission-log`))
      setMessage('내일의 관찰 로그를 저장했어요.')
      await refreshEntries()
    } catch (missionError) {
      setError(missionError instanceof Error ? missionError.message : '기록 저장에 실패했어요.')
    }
  }

  function navigateToView(next: AppView) {
    window.location.hash = next === 'studio' ? `/studio/${currentEntryId ? currentStudioPage : 'source'}` : '/'
    setView(next)
    if (next === 'studio' && !currentEntryId) {
      setActiveStudioPage('source')
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function navigateToStudioPage(next: StudioPage) {
    window.location.hash = `/studio/${next}`
    setView('studio')
    setActiveStudioPage(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function submitQuizAnswer() {
    if (quizChoice === null) {
      return
    }
    setQuizSubmitted(true)
  }

  function openCardChat(index: number, cardTitle: string, cardBody: string) {
    const kind = resultCardKinds[index] ?? 'summary'
    setActiveCardChat({ kind, cardTitle, cardBody })
    setCardChatInput('')
    setCardChatHistory([
      {
        role: 'assistant',
        content: '이 카드에 대해 궁금한 점을 바로 물어보세요.',
      },
    ])
  }

  function closeCardChat() {
    if (isCardChatLoading) {
      return
    }
    setActiveCardChat(null)
    setCardChatInput('')
  }

  async function sendCardChatMessage(rawMessage: string) {
    if (!currentEntryId || !activeCardChat) {
      return
    }
    const trimmedMessage = rawMessage.trim()
    if (!trimmedMessage) {
      return
    }

    const nextUserMessage: CardChatMessage = { role: 'user', content: trimmedMessage }
    const historyForRequest = cardChatHistory.slice(-6)

    setCardChatHistory((prev) => [...prev, nextUserMessage])
    setCardChatInput('')
    setIsCardChatLoading(true)

    try {
      const response = await api<{ cardKind: CardChatKind; reply: string }>(
        `/api/v1/entries/${currentEntryId}/cards/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cardKind: activeCardChat.kind,
            message: trimmedMessage,
            history: historyForRequest,
          }),
        },
      )

      setCardChatHistory((prev) => [...prev, { role: 'assistant', content: response.reply }])
    } catch (cardChatError) {
      setCardChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            cardChatError instanceof Error
              ? `지금은 답을 불러오지 못했어요. 잠깐 뒤에 다시 물어봐 주세요.\n${cardChatError.message}`
              : '지금은 답을 불러오지 못했어요. 잠깐 뒤에 다시 물어봐 주세요.',
        },
      ])
    } finally {
      setIsCardChatLoading(false)
    }
  }

  if (view === 'home') {
    return (
      <main className="home-shell">
        <header className="home-nav">
          <button
            type="button"
            className="studio-brand"
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }
            }}
            aria-label={`${BRAND_NAME} 홈 상단으로`}
          >
            <img src={BRAND_LOGO} alt="" aria-hidden="true" decoding="async" />
            <strong>{BRAND_NAME}</strong>
          </button>
          <div className="home-nav-actions">
            {latestEntry ? (
              <button type="button" className="home-nav-link" onClick={() => void loadEntry(latestEntry.entryId)}>
                최근 결과 보기
              </button>
            ) : null}
            <button type="button" className="home-nav-cta" onClick={() => navigateToView('studio')}>
              바로 시작하기
            </button>
          </div>
        </header>

        <section className="home-hero">
          <div className="home-hero-media">
            <div className="home-hero-copy">
              <p className="home-kicker">과학과 수학을 ‘공부’가 아닌 ‘언어’로</p>
              <h1>
                아이들이 세상을
                <br />
                <span className="hero-nowrap">이해하는 방식을 바꿉니다</span>
              </h1>
              <p className="home-hero-body">
                손글씨 일기를 읽고, 질문과 실험, 장면 이미지와 설명 영상을 아이의 속도에 맞춰 엮습니다.
              </p>
              <div className="home-hero-actions">
                <button type="button" className="home-primary" onClick={() => navigateToView('studio')}>
                  일기 올리고 시작하기
                </button>
                {latestEntry ? (
                  <button type="button" className="home-secondary" onClick={() => void loadEntry(latestEntry.entryId)}>
                    이어서 보기
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <section className="home-band home-journey-band">
          <div className="home-section-head">
            <p className="home-kicker">내일 다시 돌아오게</p>
            <h2>질문으로 끝나지 않고, 기록으로 이어집니다.</h2>
          </div>
          <div className="home-journey-grid">
            {homeJourneySteps.map((step, index) => (
              <article key={step.title} className="home-step-card">
                <span>{index + 1}</span>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-band">
          <div className="home-section-head">
            <p className="home-kicker">세 가지 맛</p>
            <h2>같은 일기도 서로 다른 탐구 톤으로 바뀝니다.</h2>
          </div>
          <div className="home-mode-grid">
            {homeModes.map((mode, index) => (
              <article key={mode.title} className={`home-mode-card tone-${index + 1}`}>
                <img
                  src={index === 0 ? '/landing/hero-story-02.webp' : index === 1 ? '/landing/hero-story-01.webp' : '/landing/hero-model.webp'}
                  alt={mode.title}
                  loading="lazy"
                  decoding="async"
                />
                <div>
                  <strong>{mode.title}</strong>
                  <p>{mode.body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="home-band home-bottom-cta">
          <div className="home-section-head">
            <p className="home-kicker">바로 시작</p>
            <h2>일기 한 장이면 충분합니다.</h2>
          </div>
          <div className="home-bottom-actions">
            <button type="button" className="home-primary" onClick={() => navigateToView('studio')}>
              작업 화면 열기
            </button>
            {latestEntry ? (
              <button type="button" className="home-secondary" onClick={() => void loadEntry(latestEntry.entryId)}>
                최근 세션 이어 보기
              </button>
            ) : null}
          </div>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <div className="studio-topbar">
        <button type="button" className="studio-brand" onClick={() => navigateToView('home')} aria-label={`${BRAND_NAME} 홈으로`}>
          <img src={BRAND_LOGO} alt="" aria-hidden="true" decoding="async" />
          <strong>{BRAND_NAME}</strong>
        </button>
        <span>작업 화면</span>
      </div>

      <section className="workspace-header">
        <div className="workspace-title">
          <p className="section-kicker">{BRAND_NAME}</p>
          <h1>
            한 번에 몰아놓지 않고, 단계별로
            <br />
            따라갑니다.
          </h1>
          <p className="workspace-summary">
            먼저 올리고, 읽힌 내용을 고치고, 그다음 결과를 확인합니다.
            <br />
            필요할 때만 다음 깊이로 내려갑니다.
          </p>
        </div>
      </section>

      <section className="studio-route-shell">
        <nav className="studio-route-bar" aria-label="작업 단계">
          {studioPages.map((page) => {
            const disabled =
              (page.id === 'ocr' && !entryStatus) ||
              (page.id === 'results' && !entryStatus) ||
              (page.id === 'library' && !entries.length)
            return (
              <button
                key={page.id}
                type="button"
                className={`studio-route-chip ${currentStudioPage === page.id ? 'active' : ''}`}
                disabled={disabled}
                onClick={() => navigateToStudioPage(page.id)}
              >
                <span>{page.step}</span>
                <strong>{page.title}</strong>
              </button>
            )
          })}
        </nav>

        <section className="studio-content studio-page-frame">
          {currentStudioPage !== 'source' ? (
            <section className="studio-progress-band">
              <div className="section-head compact">
                <div>
                  <p className="section-kicker">Live Status</p>
                  <h2>{message}</h2>
                </div>
                <strong>{currentMeta.progress}%</strong>
              </div>
              <div className="status-progress-track">
                <span className="status-progress-fill" style={{ width: `${currentMeta.progress}%` }} />
              </div>
              <div className="status-step-row">
                {pipelineSteps.map((step, index) => {
                  const activeIndex =
                    currentStatus === 'created'
                      ? 0
                      : currentStatus === 'text_ready'
                        ? 1
                        : currentStatus === 'queued' || currentStatus === 'parsing' || currentStatus === 'planning'
                          ? 2
                          : currentStatus === 'rendering_image'
                            ? 3
                            : currentStatus === 'rendering_audio' || currentStatus === 'rendering_video' || currentStatus === 'completed'
                              ? 4
                              : 0
                  const completed = index < activeIndex
                  const active = index === activeIndex
                  return (
                    <div
                      key={step.key}
                      className={`status-step ${completed ? 'completed' : ''} ${active ? 'active' : ''}`}
                    >
                      <span>{index + 1}</span>
                      <small>{step.label}</small>
                    </div>
                  )
                })}
              </div>
            </section>
          ) : null}

          {currentStudioPage === 'source' ? (
            <div className="source-stage-grid">
              <section className="composer-section">
                <div className="section-head compact">
                  <div>
                    <p className="section-kicker">Source</p>
                    <h2>일기 한 장을 올리고 바로 읽습니다</h2>
                  </div>
                </div>

                <div
                  className="upload-stage upload-stage-large"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => void onFileDrop(event)}
                >
                  <input ref={fileInputRef} type="file" accept="image/*" onChange={onFileChange} />
                  <strong>{isUploading ? 'AI가 손글씨를 살펴보는 중이에요' : '파일 선택 또는 드래그'}</strong>
                  <span>손글씨 이미지를 올리면 읽은 문장이 다음 단계에 바로 채워집니다.</span>
                  <div className="upload-actions">
                    <button type="button" className="primary-action" onClick={openFilePicker} disabled={isUploading}>
                      {isUploading ? '생각 중...' : '일기 이미지 올리기'}
                    </button>
                  </div>
                </div>

                <div className="source-tip-list" aria-label="업로드 안내">
                  <article className="source-tip-card">
                    <strong>선명하게 한 장</strong>
                    <p>기울지 않은 정면 사진이 가장 잘 읽힙니다.</p>
                  </article>
                  <article className="source-tip-card">
                    <strong>바로 수정 가능</strong>
                    <p>다음 단계에서 잘못 읽힌 글자만 고치면 됩니다.</p>
                  </article>
                  <article className="source-tip-card">
                    <strong>과학 해석으로 연결</strong>
                    <p>읽기 확인 뒤에는 질문, 실험, 퀴즈, 영상이 순서대로 생성됩니다.</p>
                  </article>
                </div>

                <div className="page-nav-row page-nav-row-source">
                  <button type="button" className="secondary-action" onClick={() => navigateToView('home')}>
                    이전 단계
                  </button>
                  <button
                    type="button"
                    className="primary-action"
                    disabled={!entryStatus || entryStatus.status !== 'text_ready'}
                    onClick={() => navigateToStudioPage('ocr')}
                  >
                    다음 단계
                  </button>
                </div>
              </section>

              <section className="composer-section source-preview-panel">
                <div className="section-head compact">
                  <div>
                    <p className="section-kicker">Preview</p>
                    <h2>{currentPoster ? '지금 올라온 원본' : '업로드 전 미리보기'}</h2>
                  </div>
                </div>
                {currentPoster ? (
                  <img
                    className="spotlight-image source-preview-image"
                    src={currentPoster}
                    alt="업로드 원본 미리보기"
                    decoding="async"
                  />
                ) : (
                  <div className="media-empty source-preview-empty">
                    <p>이미지를 올리면 여기에서 원본을 크게 확인할 수 있습니다.</p>
                  </div>
                )}
              </section>
            </div>
          ) : null}

          {currentStudioPage === 'ocr' ? (
            <div className="ocr-stage-grid">
              <section className="composer-section">
                <div className="section-head compact">
                  <div>
                    <p className="section-kicker">읽기 확인</p>
                    <h2>읽은 내용을 다듬고 탐구의 시작점을 정합니다</h2>
                  </div>
                </div>
                <textarea
                  className="editor-textarea"
                  value={transcript}
                  onChange={(event) => setTranscript(event.target.value)}
                  placeholder="자동 추출된 일기 텍스트가 여기에 나타나요."
                />
                {entryStatus?.parseWarnings?.length ? (
                  <ul className="warning-list">
                    {entryStatus.parseWarnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
                {error ? <p className="error-text">{error}</p> : null}

                <section className="content-panel ocr-reference-card">
                  <div className="section-head compact">
                    <div>
                      <p className="section-kicker">원본 비교</p>
                      <h2>원본과 읽힌 내용을 함께 보며 맞춥니다</h2>
                    </div>
                  </div>
                  <div className="ocr-reference-layout">
                    {currentPoster ? (
                      <img
                        className="spotlight-image ocr-reference-image"
                        src={currentPoster}
                        alt="OCR 원본 일기 이미지"
                        decoding="async"
                      />
                    ) : (
                      <div className="media-empty">
                        <p>업로드한 원본 일기가 여기에 나타납니다.</p>
                      </div>
                    )}
                  </div>
                </section>
              </section>

              <section className="composer-section ocr-side-panel">
                <div className="section-head compact">
                  <div>
                    <p className="section-kicker">탐구 모드</p>
                    <h2>세 가지 읽기 방식 중 하나를 고릅니다</h2>
                  </div>
                </div>

                <div className="mode-grid">
                  {sortedModes.map((mode) => {
                    const selected = preferredModeId === mode.id
                    const recommended = result?.recommendedModeId === mode.id
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        className={`mode-card ${selected ? 'selected' : ''} ${recommended ? 'recommended' : ''}`}
                        onClick={() => setPreferredModeId(mode.id)}
                      >
                        <div className="mode-card-top">
                          <strong>{mode.title}</strong>
                          {recommended ? <span>추천</span> : null}
                        </div>
                        <p>{mode.hook}</p>
                        <small>{mode.mission}</small>
                        <span className="mode-card-reward">{mode.reward}</span>
                      </button>
                    )
                  })}
                </div>

              </section>

              <section className="composer-section ocr-action-footer">
                <div className="ocr-action-copy">
                  <strong>읽은 내용을 확정하면 바로 다음 결과를 만듭니다</strong>
                  <span>
                    {isBusy ? '지금 장면, 질문, 이미지, 영상을 함께 엮는 중이에요.' : '문장을 다듬고 모드를 고르면 바로 결과 화면으로 넘어갑니다.'}
                  </span>
                </div>
                <div className="page-nav-row page-nav-row-inline">
                  <button type="button" className="secondary-action" onClick={() => navigateToStudioPage('source')}>
                    이전 단계
                  </button>
                  <button
                    type="button"
                    className="primary-action"
                    disabled={!transcript.trim() || isBusy}
                    onClick={() => void onAnalyzeRequest()}
                  >
                    {isBusy ? '생성 진행 중' : '탐구 결과 만들기'}
                  </button>
                </div>
              </section>
            </div>
          ) : null}

          {currentStudioPage === 'results' ? (
            <>
              <section className="result-stage">
                {isBusy ? (
                  <div className="generation-overlay">
                    <div className="generation-card">
                      <div className="generation-figure">
                        <div className="generation-bubble bubble-a" />
                        <div className="generation-bubble bubble-b" />
                        <div className="generation-bubble bubble-c" />
                        <img src="/loading/science-walker.webp" alt="" aria-hidden="true" decoding="async" />
                      </div>
                      <div className="generation-track" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                        <span />
                      </div>
                      <strong>{currentMeta.label}</strong>
                      <p>{currentMeta.detail}</p>
                    </div>
                  </div>
                ) : null}

                <div className="result-hero-grid">
                  <section className="content-panel result-summary-panel">
                    <div className="section-head compact">
                      <div>
                        <p className="section-kicker">Summary</p>
                        <h2>오늘의 장면을 과학 질문으로 바꿨습니다</h2>
                      </div>
                      <span>{videoDurationLabel}</span>
                    </div>
                    <p className="result-summary-copy">
                      {result?.summary ?? '생성이 끝나면 오늘의 장면을 한 문장 요약으로 보여줍니다.'}
                    </p>
                    {diaryExcerpt ? (
                      <div className="summary-origin-note">
                        <strong>원본 일기에서 읽은 내용</strong>
                        <p>{diaryExcerpt}</p>
                      </div>
                    ) : null}
                    {result ? (
                      <>
                        <div className="chip-row">
                          {result.emotions.map((emotion) => (
                            <span key={emotion} className="chip">
                              {emotion}
                            </span>
                          ))}
                        </div>
                        <ol className="question-list question-list-compact">
                          {result.questionSeeds.slice(0, 3).map((question) => (
                            <li key={question}>{question}</li>
                          ))}
                        </ol>
                      </>
                    ) : null}
                  </section>

                  <section className="media-panel result-video-panel">
                    <div className="panel-header">
                      <span>이미지 기반 설명 영상</span>
                      <strong>{result?.videoDirector.title ?? '과학 해석 영상'}</strong>
                    </div>
                    {localVideoUrl ? (
                      <video
                        key={localVideoUrl}
                        className="spotlight-video"
                        controls
                        playsInline
                        preload="metadata"
                        poster={thumbnailUrl ?? undefined}
                        onError={() => setVideoLoadError(true)}
                        onLoadedData={() => setVideoLoadError(false)}
                      >
                        <source src={localVideoUrl} type="video/mp4" />
                      </video>
                    ) : videoPreviewImage ? (
                      <img className="spotlight-video" src={videoPreviewImage} alt="영상 준비 중 장면 미리보기" decoding="async" />
                    ) : (
                      <div className="media-empty">
                        <p>생성된 영상이 여기에 나타납니다.</p>
                      </div>
                    )}
                    {localVideoUrl ? (
                      <div className="result-video-actions">
                        {videoLoadError ? <p className="video-help-text">모바일 재생이 바로 안 되면 새 창에서 영상을 열어 보세요.</p> : null}
                        <a className="secondary-action media-open-link" href={localVideoUrl} target="_blank" rel="noreferrer">
                          새 창에서 영상 열기
                        </a>
                      </div>
                    ) : null}
                    {result?.narration.audioUrl ? (
                      <div className="result-audio-panel">
                        <div className="result-audio-meta">
                          <span>내레이션 듣기</span>
                          <strong>
                            {result.narration.voice ?? '음성'}
                            {result.narration.durationSec ? ` · ${Math.round(result.narration.durationSec)}초` : ''}
                          </strong>
                        </div>
                        <audio controls preload="none" src={result.narration.audioUrl} />
                      </div>
                    ) : (
                      <div className="result-audio-empty">
                        <p>이번 결과는 음성 없이 저장되었어요.</p>
                      </div>
                    )}
                  </section>
                </div>
              </section>

              {result ? (
                <>
                  <section className="cards-grid result-card-grid">
                    {result.sceneCards.map((card, index) => (
                      <button
                        key={card.title}
                        type="button"
                        className="story-card result-scene-card result-scene-card-button"
                        onClick={() => openCardChat(index, card.title, card.body)}
                      >
                        <p className="section-kicker">Card</p>
                        <strong>{card.title}</strong>
                        <p>{card.body}</p>
                        <span className="result-scene-card-cta">눌러서 더 물어보기</span>
                      </button>
                    ))}
                  </section>

                  <div className="result-story-grid">
                    <section className="media-panel result-origin-panel">
                      <div className="panel-header">
                        <span>원본 일기</span>
                        <strong>이번 결과의 출발점</strong>
                      </div>
                      {currentPoster ? (
                        <img className="spotlight-image" src={currentPoster} alt="원본 일기 이미지" decoding="async" />
                      ) : (
                        <div className="media-empty">
                          <p>업로드한 원본 일기가 여기에 나타납니다.</p>
                        </div>
                      )}
                    </section>

                    <section className="media-panel result-image-panel">
                      <div className="panel-header">
                        <span>상황 이미지</span>
                        <strong>{result.sceneVisual.title}</strong>
                      </div>
                      {sceneVisualUrl ? (
                        <img className="spotlight-image" src={sceneVisualUrl} alt="일기 상황 재구성 이미지" decoding="async" />
                      ) : isBusy ? (
                        <div className="media-empty">
                          <p>상황 이미지를 그리는 중입니다.</p>
                        </div>
                      ) : (
                        <div className="media-empty">
                          <p>생성된 상황 이미지가 여기에 나타납니다.</p>
                        </div>
                      )}
                    </section>

                  </div>

                  <section className="content-panel result-interpretation-panel">
                    <div className="section-head compact">
                      <div>
                        <p className="section-kicker">Science Explanation</p>
                        <h2>{result.scientificInterpretation.title}</h2>
                      </div>
                    </div>
                    <dl className="detail-grid">
                      <div>
                        <dt>관찰 장면</dt>
                        <dd>{result.scientificInterpretation.observation}</dd>
                      </div>
                      <div>
                        <dt>과학 개념</dt>
                        <dd>{result.scientificInterpretation.concept}</dd>
                      </div>
                      <div>
                        <dt>설명</dt>
                        <dd>{result.scientificInterpretation.explanation}</dd>
                      </div>
                      <div>
                        <dt>측정 포인트</dt>
                        <dd>{result.scientificInterpretation.measurementIdea}</dd>
                      </div>
                      <div>
                        <dt>안전 메모</dt>
                        <dd>{result.scientificInterpretation.safetyNote}</dd>
                      </div>
                    </dl>
                    <div className="chip-row">
                      {result.scienceLens.map((lens) => (
                        <span key={lens} className="chip">
                          {lens}
                        </span>
                      ))}
                    </div>
                  </section>

                  <div className="insight-grid result-activity-grid">
                    <section className="content-panel challenge-panel">
                      <div className="section-head compact">
                        <div>
                          <p className="section-kicker">Science Quiz</p>
                          <h2>{result.scienceQuiz.title}</h2>
                        </div>
                        <span>{quizSubmitted ? (quizChoice === result.scienceQuiz.answerIndex ? '성공' : '다시 도전') : '문제 1'}</span>
                      </div>

                      <div className="challenge-media">
                        {sceneVisualUrl ? (
                          <img src={sceneVisualUrl} alt="퀴즈 장면" className="challenge-image" decoding="async" />
                        ) : isBusy ? (
                          <div className="media-empty">
                            <p>퀴즈용 장면 이미지를 준비하는 중입니다.</p>
                          </div>
                        ) : (
                          <div className="media-empty">
                            <p>퀴즈용 장면 이미지가 여기에 나타납니다.</p>
                          </div>
                        )}
                      </div>

                      <p className="lead-copy">{result.scienceQuiz.question}</p>

                      <div className="quiz-choice-grid">
                        {result.scienceQuiz.options.map((option, index) => {
                          const selected = quizChoice === index
                          const correct = quizSubmitted && index === result.scienceQuiz.answerIndex
                          const wrong = quizSubmitted && selected && index !== result.scienceQuiz.answerIndex
                          return (
                            <button
                              key={`${option}-${index}`}
                              type="button"
                              className={`quiz-choice ${selected ? 'selected' : ''} ${correct ? 'correct' : ''} ${wrong ? 'wrong' : ''}`}
                              onClick={() => {
                                setQuizChoice(index)
                                if (quizSubmitted) {
                                  setQuizSubmitted(false)
                                }
                              }}
                            >
                              <strong>{index + 1}</strong>
                              <span>{option}</span>
                            </button>
                          )
                        })}
                      </div>

                      <div className="challenge-actions">
                        <button
                          type="button"
                          className="primary-action"
                          disabled={quizChoice === null}
                          onClick={submitQuizAnswer}
                        >
                          정답 확인
                        </button>
                        <button
                          type="button"
                          className="secondary-action"
                          onClick={() => {
                            setQuizChoice(null)
                            setQuizSubmitted(false)
                          }}
                        >
                          다시 풀기
                        </button>
                      </div>

                      {quizSubmitted ? (
                        <div className={`challenge-feedback ${quizChoice === result.scienceQuiz.answerIndex ? 'success' : 'retry'}`}>
                          <strong>{quizChoice === result.scienceQuiz.answerIndex ? '정답이에요.' : '한 번 더 볼까요?'}</strong>
                          <p>{result.scienceQuiz.explanation}</p>
                        </div>
                      ) : null}
                    </section>

                    <section className="content-panel game-panel">
                      <div className="section-head compact">
                        <div>
                          <p className="section-kicker">Science Game</p>
                          <h2>{result.scienceGame.title}</h2>
                        </div>
                        <span>
                          {Math.min(gameStepIndex + 1, result.scienceGame.howToPlay.length)} / {result.scienceGame.howToPlay.length}
                        </span>
                      </div>
                      <div className="duo-progress" aria-hidden="true">
                        {result.scienceGame.howToPlay.map((step, index) => (
                          <span key={step} className={index <= gameStepIndex ? 'active' : ''} />
                        ))}
                      </div>
                      <p className="lead-copy">{result.scienceGame.premise}</p>
                      <div className="game-step-card">
                        <strong>이번 단계</strong>
                        <p>{result.scienceGame.howToPlay[gameStepIndex] ?? result.scienceGame.howToPlay[0]}</p>
                      </div>
                      <p className="goal-copy">{result.scienceGame.goal}</p>
                      <div className="detail-grid">
                        <div>
                          <dt>승리 조건</dt>
                          <dd>{result.scienceGame.winCondition}</dd>
                        </div>
                        <div>
                          <dt>AI 가이드</dt>
                          <dd>{result.scienceGame.aiGuide}</dd>
                        </div>
                      </div>
                      <div className="challenge-actions">
                        <button
                          type="button"
                          className="secondary-action"
                          disabled={gameStepIndex === 0}
                          onClick={() => setGameStepIndex((prev) => Math.max(0, prev - 1))}
                        >
                          이전 단계
                        </button>
                        <button
                          type="button"
                          className="primary-action"
                          disabled={gameStepIndex >= result.scienceGame.howToPlay.length - 1}
                          onClick={() =>
                            setGameStepIndex((prev) => Math.min(result.scienceGame.howToPlay.length - 1, prev + 1))
                          }
                        >
                          다음 단계
                        </button>
                      </div>
                    </section>
                  </div>

                  <div className="insight-grid result-followup-grid">
                    <section className="content-panel result-mission-panel">
                      <div className="section-head compact">
                        <div>
                          <p className="section-kicker">Mission Loop</p>
                          <h2>{result.experimentCard.title}</h2>
                        </div>
                        <span>{result.experimentCard.durationDays}일</span>
                      </div>
                      <dl className="detail-grid">
                        <div>
                          <dt>가설</dt>
                          <dd>{result.experimentCard.hypothesis}</dd>
                        </div>
                        <div>
                          <dt>독립 변수</dt>
                          <dd>{result.experimentCard.independentVariable}</dd>
                        </div>
                        <div>
                          <dt>종속 변수</dt>
                          <dd>{result.experimentCard.dependentVariable}</dd>
                        </div>
                        <div>
                          <dt>기록 방법</dt>
                          <dd>{result.experimentCard.method}</dd>
                        </div>
                        <div>
                          <dt>관찰 포인트</dt>
                          <dd>{result.experimentCard.whatToWatch}</dd>
                        </div>
                      </dl>

                      <form className="mission-form" onSubmit={(event) => void onSaveMission(event)}>
                        <label>
                          오늘 관찰한 사실
                          <textarea
                            value={missionDraft.observationData}
                            onChange={(event) =>
                              setMissionDraft((prev) => ({ ...prev, observationData: event.target.value }))
                            }
                            placeholder="예: 경사가 가팔라질수록 더 빨리 내려갔어."
                          />
                        </label>
                        <label>
                          짧은 회고
                          <textarea
                            value={missionDraft.reflection}
                            onChange={(event) =>
                              setMissionDraft((prev) => ({ ...prev, reflection: event.target.value }))
                            }
                            placeholder="예: 눈 상태도 같이 보니 속도 차이가 더 잘 보였어."
                          />
                        </label>
                        <button type="submit" className="secondary-action" disabled={!currentEntryId}>
                          관찰 로그 저장
                        </button>
                      </form>
                    </section>

                    <div className="result-followup-stack">
                      <section className="content-panel result-log-panel">
                        <div className="section-head compact">
                          <div>
                            <p className="section-kicker">관찰 로그</p>
                            <h2>내일 다시 이어서 보기</h2>
                          </div>
                        </div>
                        <div className="mission-log-list">
                          {missionLogs.length ? (
                            missionLogs.map((log) => (
                              <article key={log.id} className="mission-log-item">
                                <strong>{formatDate(log.createdAt)}</strong>
                                <p>{log.observationData}</p>
                                <span>{log.reflection}</span>
                              </article>
                            ))
                          ) : (
                            <div className="log-empty">아직 저장된 관찰 로그가 없습니다.</div>
                          )}
                        </div>
                      </section>

                      <section className="content-panel result-scenario-panel">
                        <div className="section-head compact">
                          <div>
                            <p className="section-kicker">Scenario</p>
                            <h2>{result.videoDirector.title}</h2>
                          </div>
                          <span>{result.media.videoModel ?? 'storyboard-mix'}</span>
                        </div>
                        <pre className="scenario-text">{result.videoDirector.scenarioText}</pre>
                      </section>
                    </div>
                  </div>
                </>
              ) : (
                <section className="empty-result">
                  <strong>생성된 결과가 여기에 채워집니다.</strong>
                  <span>읽기 확인 단계에서 문장을 다듬고 생성 버튼을 누르면 이 페이지가 채워집니다.</span>
                </section>
              )}

              <div className="page-nav-row">
                <button
                  type="button"
                  className="secondary-action"
                  data-testid="results-prev-step"
                  onClick={() => navigateToStudioPage('ocr')}
                >
                  이전 단계
                </button>
                <button
                  type="button"
                  className="primary-action"
                  data-testid="results-next-step"
                  onClick={() => navigateToStudioPage('library')}
                >
                  다음 단계
                </button>
              </div>
            </>
          ) : null}

          {currentStudioPage === 'library' ? (
            <section className="library-band studio-library-page">
              <div className="section-head">
                <div>
                  <p className="section-kicker">Library</p>
                  <h2>최근 결과</h2>
                </div>
              </div>
              <div className="library-scroll">
                {entries.length ? (
                  entries.map((entry) => (
                    <button key={entry.entryId} type="button" className="library-item" onClick={() => void loadEntry(entry.entryId)}>
                      {entry.posterUrl ? (
                        <img
                          src={resolveMediaUrl(entry.posterUrl) ?? undefined}
                          alt={entry.summary ?? entry.entryId}
                          loading="lazy"
                          decoding="async"
                        />
                      ) : (
                        <div className="library-placeholder">ENTRY</div>
                      )}
                      <div>
                        <strong>{entry.summary ?? '아직 생성 전인 세션'}</strong>
                        <span>{formatDate(entry.createdAt)}</span>
                        <small>{statusMeta[entry.status].label} · 로그 {entry.missionLogCount}</small>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="library-empty">아직 저장된 세션이 없습니다.</div>
                )}
              </div>
              <div className="page-nav-row">
                <button type="button" className="secondary-action" onClick={() => navigateToStudioPage('results')}>
                  이전 단계
                </button>
                <button type="button" className="primary-action" onClick={() => navigateToStudioPage('source')}>
                  새 일기 올리기
                </button>
              </div>
            </section>
          ) : null}
        </section>
      </section>

      {activeCardChat ? (
        <div className="card-chat-overlay" role="dialog" aria-modal="true" aria-labelledby="card-chat-title">
          <div className="card-chat-modal">
            <div className="card-chat-header">
              <div>
                <p className="section-kicker">Card Chat</p>
                <h2 id="card-chat-title">{cardChatMeta[activeCardChat.kind].title}</h2>
                <p className="card-chat-helper">{cardChatMeta[activeCardChat.kind].helper}</p>
              </div>
              <button type="button" className="card-chat-close" onClick={closeCardChat} aria-label="모달 닫기">
                닫기
              </button>
            </div>

            <div className="card-chat-context-inline">
              <strong>{activeCardChat.cardTitle}</strong>
              <span>{activeCardChat.cardBody}</span>
            </div>

            <div className="card-chat-log">
              {cardChatHistory.map((item, index) => (
                <div key={`${item.role}-${index}`} className={`card-chat-bubble ${item.role === 'user' ? 'user' : 'assistant'}`}>
                  <strong>{item.role === 'user' ? '나' : 'kwail'}</strong>
                  <p>{item.content}</p>
                </div>
              ))}
              {isCardChatLoading ? (
                <div className="card-chat-bubble assistant loading">
                  <strong>kwail</strong>
                  <p>선택한 카드 문맥과 시나리오를 보고 답을 정리하는 중이에요.</p>
                </div>
              ) : null}
            </div>

            <form
              className="card-chat-form"
              onSubmit={(event) => {
                event.preventDefault()
                void sendCardChatMessage(cardChatInput)
              }}
            >
              <textarea
                value={cardChatInput}
                onChange={(event) => setCardChatInput(event.target.value)}
                placeholder="이 카드에 대해 더 궁금한 점을 적어 보세요."
              />
              <div className="card-chat-actions">
                <button type="button" className="secondary-action" onClick={closeCardChat} disabled={isCardChatLoading}>
                  닫기
                </button>
                <button type="submit" className="primary-action" disabled={isCardChatLoading || !cardChatInput.trim()}>
                  질문 보내기
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default App
