import './style.css'

// Quiz State Management
class QuizState {
  constructor() {
    this.studentName = ''
    this.mode = 'practice' // 'practice' or 'test'
    this.questions = []
    this.currentQuestionIndex = 0
    this.answers = new Map()
    this.startTime = null
    this.endTime = null
    this.score = 0
    this.maxScore = 0
    this.visitedQuestions = new Set() // Track questions that have been navigated away from
  }

  async init(studentName, mode) {
    this.studentName = studentName
    this.mode = mode
    
    try {
      // Fetch questions from API based on mode
      const response = await fetch(`/api/questions/${mode}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch questions: ${response.status} ${response.statusText}`)
      }
      
      const questionsData = await response.json()
      this.questions = questionsData.questions || []
      
      if (this.questions.length === 0) {
        throw new Error('No questions received from server')
      }
      
      console.log(`Loaded ${this.questions.length} questions for ${mode} mode`)
    } catch (error) {
      console.error('Failed to load questions:', error)
      throw new Error(`Could not load quiz questions: ${error.message}`)
    }
    
    this.currentQuestionIndex = 0
    this.answers = new Map()
    this.startTime = new Date()
    this.maxScore = this.questions.reduce((sum, q) => sum + q.points, 0)
    
    // Load from localStorage if in test mode
    if (mode === 'test') {
      this.loadFromStorage()
    }
  }

  getCurrentQuestion() {
    return this.questions[this.currentQuestionIndex]
  }

  hasNextQuestion() {
    return this.currentQuestionIndex < this.questions.length - 1
  }

  hasPrevQuestion() {
    return this.currentQuestionIndex > 0
  }

  nextQuestion() {
    if (this.hasNextQuestion()) {
      this.currentQuestionIndex++
      return true
    }
    return false
  }

  prevQuestion() {
    if (this.hasPrevQuestion()) {
      this.currentQuestionIndex--
      return true
    }
    return false
  }

  saveAnswer(answer) {
    const questionId = this.getCurrentQuestion().id
    this.answers.set(questionId, {
      answer,
      timestamp: new Date(),
      questionIndex: this.currentQuestionIndex
    })
  }

  getAnswer(questionId) {
    const answerData = this.answers.get(questionId)
    return answerData ? answerData.answer : null
  }

  calculateScore() {
    this.score = 0
    
    for (const question of this.questions) {
      const userAnswer = this.getAnswer(question.id)
      if (userAnswer !== null && userAnswer !== undefined && this.isAnswerCorrect(question, userAnswer)) {
        this.score += question.points
      }
    }
    
    return this.score
  }

  isAnswerCorrect(question, userAnswer) {
    switch (question.type) {
      case 'TRUE_FALSE':
        return userAnswer === question.correct_answer

      case 'SIMPLE_FILL_IN_THE_BLANK':
        // Check if correct_answers exists
        if (!question.correct_answers || !Array.isArray(question.correct_answers)) {
          return false
        }
        
        // For multiple answers, check if user provided answers match any of the correct ones
        if (Array.isArray(userAnswer)) {
          // Multiple text boxes - check if any user answer matches any correct answer
          return userAnswer.some(answer => 
            answer && answer.trim() && 
            question.correct_answers.some(correct => 
              this.compareStrings(answer, correct)
            )
          )
        } else {
          // Single text box (legacy support)
          return question.correct_answers.some(correct => 
            this.compareStrings(userAnswer, correct)
          )
        }

      case 'STRUCTURED_FILL_IN_THE_BLANK':
        if (!Array.isArray(userAnswer) || !question.parts || !Array.isArray(question.parts)) {
          return false
        }
        return question.parts.every((part, index) => 
          userAnswer[index] && this.compareStrings(userAnswer[index], part.correct_answer)
        )

      case 'SHORT_ANSWER':
        return userAnswer && userAnswer.trim().length > 0 // Any non-empty answer gets points

      default:
        return false
    }
  }

  compareStrings(str1, str2) {
    if (!str1 || !str2) return false
    return str1.toLowerCase().trim() === str2.toLowerCase().trim()
  }

  getProgress() {
    return ((this.currentQuestionIndex + 1) / this.questions.length) * 100
  }

  async finish() {
    this.endTime = new Date()
    
    // For test mode, submit to server before clearing storage
    if (this.mode === 'test') {
      await this.submitToServer()
      this.clearStorage()
      // In test mode, don't calculate score locally - backend handles it
      return 0
    }
    
    // Only calculate score for practice mode
    return this.calculateScore()
  }

  // Submit test answers to server with retry logic
  async submitToServer(maxRetries = 3) {
    const submissionData = {
      studentName: this.studentName,
      startTime: this.startTime.toISOString(),
      endTime: this.endTime.toISOString(),
      totalQuestions: this.questions.length,
      answers: Array.from(this.answers.entries()).map(([questionId, answerData]) => ({
        questionId,
        answer: answerData.answer,
        timestamp: answerData.timestamp.toISOString(),
        questionIndex: answerData.questionIndex
      }))
    }

    let lastError = null
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        console.log(`Submitting test results (attempt ${attempt + 1}/${maxRetries})...`)
        
        const response = await fetch('/api/submit-test', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(submissionData)
        })

        if (response.ok) {
          const result = await response.json()
          console.log('Test submitted successfully:', result)
          return result
        } else {
          throw new Error(`Server responded with ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        lastError = error
        console.warn(`Submission attempt ${attempt + 1} failed:`, error.message)
        
        // If this isn't the last attempt, wait with exponential backoff
        if (attempt < maxRetries - 1) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000) // Max 10 second delay
          console.log(`Retrying in ${delay}ms...`)
          await new Promise(resolve => setTimeout(resolve, delay))
        }
      }
    }
    
    // All retries failed
    console.error('Failed to submit test after all retries:', lastError)
    throw new Error(`Failed to submit test: ${lastError.message}`)
  }

  // localStorage methods for test mode persistence
  saveToStorage() {
    if (this.mode !== 'test') return
    
    const data = {
      studentName: this.studentName,
      currentQuestionIndex: this.currentQuestionIndex,
      answers: Array.from(this.answers.entries()),
      startTime: this.startTime.toISOString()
    }
    
    localStorage.setItem('quiz-progress', JSON.stringify(data))
  }
  
  loadFromStorage() {
    const saved = localStorage.getItem('quiz-progress')
    if (!saved) return
    
    try {
      const data = JSON.parse(saved)
      this.currentQuestionIndex = data.currentQuestionIndex || 0
      this.answers = new Map(data.answers || [])
      if (data.startTime) {
        this.startTime = new Date(data.startTime)
      }
    } catch (e) {
      console.error('Failed to load quiz progress:', e)
      this.clearStorage()
    }
  }
  
  clearStorage() {
    localStorage.removeItem('quiz-progress')
  }
  
  startOver() {
    this.clearStorage()
    location.reload()
  }
}

// Question Renderers
class QuestionRenderer {
  static render(question, currentAnswer, mode, showFeedback = false, quizInstance = null) {
    const container = document.createElement('div')
    container.className = 'space-y-6'

    // Question header
    const header = this.createQuestionHeader(question)
    container.appendChild(header)

    // Question content based on type
    const content = this.createQuestionContent(question, currentAnswer, mode, showFeedback, quizInstance)
    container.appendChild(content)

    // Add "Show Correct Answers" button for practice mode
    // Show button for practice and random modes, regardless of answer status
    if ((mode === 'practice' || mode === 'random') && !showFeedback) {
      const showAnswersBtn = document.createElement('button')
      showAnswersBtn.className = 'btn-secondary w-full mt-4'
      showAnswersBtn.textContent = '💡 Show Correct Answers'
      showAnswersBtn.id = 'show-answers-btn'
      showAnswersBtn.style.backgroundColor = '#3B82F6'
      showAnswersBtn.style.color = 'white'
      showAnswersBtn.style.padding = '12px 24px'
      showAnswersBtn.style.borderRadius = '8px'
      showAnswersBtn.style.border = 'none'
      showAnswersBtn.style.cursor = 'pointer'
      container.appendChild(showAnswersBtn)
    }

    return container
  }

  static createQuestionHeader(question) {
    const header = document.createElement('div')
    header.className = 'border-b border-gray-200 pb-4'
    header.innerHTML = `
      <h2 class="text-xl font-semibold text-gray-900 mb-2">
        ${question.question_text}
      </h2>
      <div class="flex items-center justify-between text-sm text-gray-600">
      <span class="bg-sky-100 text-sky-700 px-2 py-1 rounded-full font-medium">
          ${question.type.replace(/_/g, ' ')}
        </span>
        <span class="font-medium">${question.points} point${question.points !== 1 ? 's' : ''}</span>
      </div>
      ${question.citation ? `<p class="text-sm text-gray-500 mt-2 italic">${question.citation}</p>` : ''}
    `
    return header
  }

  static createQuestionContent(question, currentAnswer, mode, showFeedback = false, quizInstance = null) {
    switch (question.type) {
      case 'TRUE_FALSE':
        return this.createTrueFalseQuestion(question, currentAnswer, mode, showFeedback, quizInstance)
      case 'SIMPLE_FILL_IN_THE_BLANK':
        return this.createSimpleFillQuestion(question, currentAnswer, mode, showFeedback, quizInstance)
      case 'STRUCTURED_FILL_IN_THE_BLANK':
        return this.createStructuredFillQuestion(question, currentAnswer, mode, showFeedback, quizInstance)
      case 'SHORT_ANSWER':
        return this.createShortAnswerQuestion(question, currentAnswer, mode, showFeedback, quizInstance)
      default:
        return this.createErrorContent()
    }
  }

  static createTrueFalseQuestion(question, currentAnswer, mode, showFeedback = false) {
    const container = document.createElement('div')
    container.className = 'space-y-4'

    const optionsContainer = document.createElement('div')
    optionsContainer.className = 'space-y-3'

    const trueOption = this.createRadioOption('answer', 'true', 'True', currentAnswer === true)
    const falseOption = this.createRadioOption('answer', 'false', 'False', currentAnswer === false)

    optionsContainer.appendChild(trueOption)
    optionsContainer.appendChild(falseOption)
    container.appendChild(optionsContainer)

    // Show feedback if requested (only for practice/random modes, not test)
    if (showFeedback && (mode === 'practice' || mode === 'random')) {
      if (currentAnswer !== null && currentAnswer !== undefined) {
        const feedback = this.createFeedback(currentAnswer === question.correct_answer, question.correct_answer ? 'True' : 'False')
        container.appendChild(feedback)
      } else {
        const feedback = this.createNoAnswerFeedback(question.correct_answer ? 'True' : 'False')
        container.appendChild(feedback)
      }
    }

    return container
  }

  static createSimpleFillQuestion(question, currentAnswer, mode, showFeedback = false) {
    const container = document.createElement('div')
    container.className = 'space-y-4'

    // For test mode, use expected_answers count, for practice mode use correct_answers length
    const numAnswers = question.expected_answers || (question.correct_answers ? question.correct_answers.length : 1)
    
    // If there are multiple correct answers, create multiple text boxes
    if (numAnswers > 1) {
      const instruction = document.createElement('p')
      instruction.className = 'text-sm text-gray-600 mb-4'
      instruction.textContent = `Please provide ${numAnswers} answers (one in each box). The order doesn't matter.`
      container.appendChild(instruction)
      
      const inputsContainer = document.createElement('div')
      inputsContainer.className = 'space-y-3'
      
      for (let i = 0; i < numAnswers; i++) {
        const inputGroup = document.createElement('div')
        inputGroup.className = 'flex items-center space-x-3'
        
        const label = document.createElement('span')
        label.className = 'text-sm font-medium text-gray-700 w-8'
        label.textContent = `${i + 1}.`
        
        const input = document.createElement('input')
        input.type = 'text'
        input.name = `answer-${i}`
        input.className = 'input-field flex-1'
        input.placeholder = `Answer ${i + 1}...`
        input.value = (Array.isArray(currentAnswer) && currentAnswer[i]) || ''
        input.autocomplete = 'off'
        
        inputGroup.appendChild(label)
        inputGroup.appendChild(input)
        inputsContainer.appendChild(inputGroup)
      }
      
      container.appendChild(inputsContainer)
    } else {
      // Single answer - use textarea as before
      const input = document.createElement('textarea')
      input.name = 'answer'
      input.className = 'textarea-field'
      input.placeholder = 'Type your answer here...'
      input.rows = 4
      input.value = currentAnswer || ''
      input.autocomplete = 'off'
      container.appendChild(input)
    }

    // Show feedback if requested (only for practice/random modes, not test)
    if (showFeedback && (mode === 'practice' || mode === 'random')) {
      this.addSimpleFillFeedback(container, question, currentAnswer)
    }

    return container
  }
  
  static addSimpleFillFeedback(container, question, currentAnswer) {
    const numAnswers = question.correct_answers.length
    
    if (numAnswers > 1 && Array.isArray(currentAnswer)) {
      // Multiple text boxes feedback
      const feedbackContainer = document.createElement('div')
      feedbackContainer.className = 'mt-4 space-y-2'
      
      let hasAnyCorrect = false
      let hasAnyAnswer = false
      
      currentAnswer.forEach((answer, index) => {
        if (answer && answer.trim().length > 0) {
          hasAnyAnswer = true
          const isCorrect = question.correct_answers.some(correct => 
            this.compareStrings(answer, correct)
          )
          if (isCorrect) hasAnyCorrect = true
          
          const feedback = this.createFeedback(isCorrect, 
            isCorrect ? answer : `Correct options: ${question.correct_answers.join(', ')}`, 
            `Answer ${index + 1}`)
          feedbackContainer.appendChild(feedback)
        } else {
          const feedback = this.createNoAnswerFeedback(
            `Correct options: ${question.correct_answers.join(', ')}`, 
            `Answer ${index + 1}`)
          feedbackContainer.appendChild(feedback)
        }
      })
      
      if (!hasAnyAnswer) {
        const feedback = this.createNoAnswerFeedback(
          `Correct answers: ${question.correct_answers.join(', ')}`)
        feedbackContainer.appendChild(feedback)
      }
      
      container.appendChild(feedbackContainer)
    } else {
      // Single answer feedback (original logic)
      if (currentAnswer && currentAnswer.trim().length > 0) {
        const isCorrect = question.correct_answers.some(correct => 
          this.compareStrings(currentAnswer, correct)
        )
        const correctAnswers = question.correct_answers.join(', ')
        const feedback = this.createFeedback(isCorrect, correctAnswers)
        container.appendChild(feedback)
      } else {
        const correctAnswers = question.correct_answers.join(', ')
        const feedback = this.createNoAnswerFeedback(correctAnswers)
        container.appendChild(feedback)
      }
    }
  }

  static createStructuredFillQuestion(question, currentAnswer, mode, showFeedback = false) {
    const container = document.createElement('div')
    container.className = 'space-y-4'

    const partsContainer = document.createElement('div')
    partsContainer.className = 'space-y-4'

    question.parts.forEach((part, index) => {
      const partContainer = document.createElement('div')
      partContainer.className = 'bg-gray-50 p-4 rounded-lg'

      const label = document.createElement('label')
      label.className = 'block text-sm font-medium text-gray-700 mb-2'
      label.textContent = part.prompt

      const input = document.createElement('input')
      input.type = 'text'
      input.name = `answer-${index}`
      input.className = 'input-field'
      input.placeholder = 'Your answer...'
      input.value = (currentAnswer && currentAnswer[index]) || ''
      input.autocomplete = 'off'

      partContainer.appendChild(label)
      partContainer.appendChild(input)

      if (part.citation) {
        const citation = document.createElement('p')
        citation.className = 'text-xs text-gray-500 mt-1 italic'
        citation.textContent = part.citation
        partContainer.appendChild(citation)
      }

      partsContainer.appendChild(partContainer)
    })

    container.appendChild(partsContainer)

    // Show feedback if requested (only for practice/random modes, not test)
    if (showFeedback && (mode === 'practice' || mode === 'random')) {
      const feedbacks = document.createElement('div')
      feedbacks.className = 'space-y-2 mt-4'
      
      question.parts.forEach((part, index) => {
        if (currentAnswer && currentAnswer[index] && currentAnswer[index].trim().length > 0) {
          // User provided an answer for this part
          const isCorrect = this.compareStrings(currentAnswer[index], part.correct_answer)
          const feedback = this.createFeedback(isCorrect, part.correct_answer, part.prompt)
          feedbacks.appendChild(feedback)
        } else {
          // No answer provided for this part
          const feedback = this.createNoAnswerFeedback(part.correct_answer, part.prompt)
          feedbacks.appendChild(feedback)
        }
      })
      
      container.appendChild(feedbacks)
    }

    return container
  }

  static createShortAnswerQuestion(question, currentAnswer, mode, showFeedback = false) {
    const container = document.createElement('div')
    container.className = 'space-y-4'

    // Only show grading notes in teacher mode (not in student-facing modes)
    // Grading notes are for teacher reference only

    const textarea = document.createElement('textarea')
    textarea.name = 'answer'
    textarea.className = 'textarea-field'
    textarea.placeholder = 'Write your detailed answer here...'
    textarea.rows = 6
    textarea.value = currentAnswer || ''
    textarea.autocomplete = 'off'

    container.appendChild(textarea)

    // Show feedback if requested and there's an answer (only for practice/random modes, not test)
    if (showFeedback && currentAnswer && currentAnswer.trim().length > 0 && (mode === 'practice' || mode === 'random')) {
      const feedback = document.createElement('div')
      feedback.className = 'mt-4 p-4 rounded-lg border bg-blue-50 border-blue-200 text-blue-800'
      feedback.innerHTML = `
        <div class="flex items-start">
          <span class="text-lg font-bold mr-2">ℹ️</span>
          <div>
            <p class="font-semibold">Answer Submitted</p>
            <p class="text-sm mt-1">Short answer questions require manual grading. Your response has been recorded.</p>
          </div>
        </div>
      `
      container.appendChild(feedback)
    }

    return container
  }

  static createRadioOption(name, value, label, checked = false) {
    const container = document.createElement('label')
    container.className = 'flex items-center p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors'

    const input = document.createElement('input')
    input.type = 'radio'
    input.name = name
    input.value = value
    input.className = 'w-4 h-4 text-sky-600 border-gray-300 focus:ring-sky-100'
    input.checked = checked
    input.autocomplete = 'off'

    const span = document.createElement('span')
    span.className = 'ml-3 text-gray-900 font-medium'
    span.textContent = label

    container.appendChild(input)
    container.appendChild(span)

    return container
  }

  static createFeedback(isCorrect, correctAnswer, prompt = '') {
    const feedback = document.createElement('div')
    feedback.className = `mt-4 p-4 rounded-lg border ${
      isCorrect 
        ? 'bg-green-50 border-green-200 text-green-800' 
        : 'bg-red-50 border-red-200 text-red-800'
    }`

    const icon = isCorrect ? '✓' : '✗'
    const status = isCorrect ? 'Correct!' : 'Incorrect'
    
    feedback.innerHTML = `
      <div class="flex items-start">
        <span class="text-lg font-bold mr-2">${icon}</span>
        <div>
          <p class="font-semibold">${status}</p>
          ${!isCorrect ? `<p class="text-sm mt-1">${prompt ? `<strong>${prompt}</strong><br>` : ''}Correct answer: ${correctAnswer}</p>` : ''}
        </div>
      </div>
    `

    return feedback
  }

  static createNoAnswerFeedback(correctAnswer, prompt = '') {
    const feedback = document.createElement('div')
    feedback.className = 'mt-4 p-4 rounded-lg border bg-yellow-50 border-yellow-200 text-yellow-800'
    
    feedback.innerHTML = `
      <div class="flex items-start">
        <span class="text-lg font-bold mr-2">⚠</span>
        <div>
          <p class="font-semibold">No Answer Provided</p>
          <p class="text-sm mt-1">${prompt ? `<strong>${prompt}</strong><br>` : ''}Correct answer: ${correctAnswer}</p>
        </div>
      </div>
    `

    return feedback
  }

  static createErrorContent() {
    const container = document.createElement('div')
    container.className = 'text-center text-red-600 p-8'
    container.innerHTML = `
      <p class="text-lg font-semibold">Error loading question</p>
      <p class="text-sm mt-2">Please try refreshing the page</p>
    `
    return container
  }

  // Helper method to check if there's a valid answer for different question types
  static hasValidAnswer(questionType, currentAnswer) {
    switch (questionType) {
      case 'TRUE_FALSE':
        return currentAnswer === true || currentAnswer === false
      
      case 'SIMPLE_FILL_IN_THE_BLANK':
        if (Array.isArray(currentAnswer)) {
          return currentAnswer.some(answer => answer && answer.trim().length > 0)
        }
        return currentAnswer && currentAnswer.trim().length > 0
      
      case 'SHORT_ANSWER':
        return currentAnswer && currentAnswer.trim().length > 0
      
      case 'STRUCTURED_FILL_IN_THE_BLANK':
        return currentAnswer && Array.isArray(currentAnswer) && 
               currentAnswer.some(answer => answer && answer.trim().length > 0)
      
      default:
        return false
    }
  }

  // Static string comparison helper method for feedback
  static compareStrings(str1, str2) {
    if (!str1 || !str2) return false
    return str1.toLowerCase().trim() === str2.toLowerCase().trim()
  }
}

// UI Controller
class UIController {
  constructor(quizState) {
    this.quiz = quizState
    this.currentScreen = 'loading'
    this.initializeElements()
    this.bindEvents()
  }

  initializeElements() {
    this.screens = {
      loading: document.getElementById('loading-screen'),
      welcome: document.getElementById('welcome-screen'),
      quiz: document.getElementById('quiz-screen'),
      results: document.getElementById('results-screen'),
      review: document.getElementById('review-screen')
    }

    this.elements = {
      studentForm: document.getElementById('student-form'),
      studentNameDisplay: document.getElementById('student-name-display'),
      modeIndicator: document.getElementById('mode-indicator'),
      questionCounter: document.getElementById('question-counter'),
      progressFill: document.getElementById('progress-fill'),
      questionContainer: document.getElementById('question-container'),
      prevBtn: document.getElementById('prev-btn'),
      nextBtn: document.getElementById('next-btn'),
      skipBtn: document.getElementById('skip-btn'),
      startOverBtn: document.getElementById('start-over-btn'),
      resultsContent: document.getElementById('results-content'),
      restartBtn: document.getElementById('restart-btn'),
      reviewBtn: document.getElementById('review-btn'),
      
      // Review screen elements
      reviewContent: document.getElementById('review-content'),
      reviewStudentName: document.getElementById('review-student-name'),
      reviewModeIndicator: document.getElementById('review-mode-indicator'),
      backToResultsBtn: document.getElementById('back-to-results-btn'),
      
      // Welcome screen elements
      savedProgressNotice: document.getElementById('saved-progress-notice'),
      savedStudentName: document.getElementById('saved-student-name'),
      savedQuestionNumber: document.getElementById('saved-question-number'),
      totalQuestions: document.getElementById('total-questions'),
      resumeTestBtn: document.getElementById('resume-test-btn'),
      startFreshBtn: document.getElementById('start-fresh-btn')
    }
  }

  bindEvents() {
    this.elements.studentForm.addEventListener('submit', this.handleStartQuiz.bind(this))
    this.elements.prevBtn.addEventListener('click', this.handlePrevQuestion.bind(this))
    this.elements.nextBtn.addEventListener('click', this.handleNextQuestion.bind(this))
    this.elements.skipBtn.addEventListener('click', this.handleSkipQuestion.bind(this))
    this.elements.startOverBtn.addEventListener('click', this.handleStartOver.bind(this))
    this.elements.restartBtn.addEventListener('click', this.handleRestart.bind(this))
    this.elements.reviewBtn.addEventListener('click', this.handleReview.bind(this))
    this.elements.backToResultsBtn.addEventListener('click', this.handleBackToResults.bind(this))
    
    // Resume/Start Fresh buttons
    this.elements.resumeTestBtn.addEventListener('click', this.handleResumeTest.bind(this))
    this.elements.startFreshBtn.addEventListener('click', this.handleStartFresh.bind(this))
    
    // Teacher Portal button
    const teacherPortalBtn = document.getElementById('teacher-portal-btn')
    if (teacherPortalBtn) {
      teacherPortalBtn.addEventListener('click', this.handleTeacherPortal.bind(this))
    }

    // Auto-save answers
    this.elements.questionContainer.addEventListener('input', this.handleAnswerChange.bind(this))
    this.elements.questionContainer.addEventListener('change', this.handleAnswerChange.bind(this))
    
    // Handle show answers button (using event delegation)
    this.elements.questionContainer.addEventListener('click', this.handleShowAnswers.bind(this))
  }

  showScreen(screenName) {
    Object.values(this.screens).forEach(screen => {
      screen.classList.add('hidden')
    })
    this.screens[screenName].classList.remove('hidden')
    this.currentScreen = screenName
    
    // Check for saved progress when showing welcome screen
    if (screenName === 'welcome') {
      this.checkSavedProgress()
    }
  }

  showQuizLoadingState() {
    // Reuse the existing loading screen
    this.showScreen('loading')
  }

  async handleStartQuiz(e) {
    e.preventDefault()
    const formData = new FormData(e.target)
    const studentName = formData.get('studentName').trim()
    const mode = formData.get('mode')

    if (!studentName) {
      alert('Please enter your name')
      return
    }

    // For test mode, clear any existing progress to start fresh
    if (mode === 'test') {
      localStorage.removeItem('quiz-progress')
    }

    try {
      // Show loading while fetching questions
      this.showQuizLoadingState()
      
      await this.quiz.init(studentName, mode)
      this.initQuizUI()
      this.showScreen('quiz')
      this.renderCurrentQuestion()
    } catch (error) {
      console.error('Failed to start quiz:', error)
      alert(`Failed to start quiz: ${error.message}`)
      this.showScreen('welcome')
    }
  }

  initQuizUI() {
    this.elements.studentNameDisplay.textContent = this.quiz.studentName
    
    // Set mode display text and styling
    let modeText, modeClass
    switch (this.quiz.mode) {
      case 'practice':
        modeText = 'Practice Mode'
        modeClass = 'bg-green-100 text-green-700'
        break
      case 'random':
        modeText = 'Random Practice'
        modeClass = 'bg-purple-100 text-purple-700'
        break
      case 'test':
        modeText = 'Final Exam'
        modeClass = 'bg-blue-100 text-blue-700'
        break
      default:
        modeText = 'Quiz Mode'
        modeClass = 'bg-gray-100 text-gray-700'
    }
    
    this.elements.modeIndicator.textContent = modeText
    this.elements.modeIndicator.className = `text-sm font-medium px-3 py-1 rounded-full ${modeClass}`
    
    // Show/hide Start Over button based on mode
    if (this.quiz.mode === 'test') {
      this.elements.startOverBtn.classList.remove('hidden')
    } else {
      this.elements.startOverBtn.classList.add('hidden')
    }
    
    this.updateProgress()
    this.updateNavigation()
  }

  renderCurrentQuestion() {
    const question = this.quiz.getCurrentQuestion()
    const currentAnswer = this.quiz.getAnswer(question.id)
    
    // Clear container with animation
    this.elements.questionContainer.style.opacity = '0'
    this.elements.questionContainer.style.transform = 'translateX(20px)'
    
    setTimeout(() => {
      const questionElement = QuestionRenderer.render(question, currentAnswer, this.quiz.mode)
      this.elements.questionContainer.innerHTML = ''
      this.elements.questionContainer.appendChild(questionElement)
      
      this.elements.questionContainer.style.opacity = '1'
      this.elements.questionContainer.style.transform = 'translateX(0)'
      
      this.updateQuestionCounter()
      this.updateProgress()
      this.updateNavigation()
    }, 150)
  }

  handleAnswerChange(e) {
    const question = this.quiz.getCurrentQuestion()
    let answer = null
    let shouldSave = false

    switch (question.type) {
      case 'TRUE_FALSE':
        const checkedRadio = this.elements.questionContainer.querySelector('input[name="answer"]:checked')
        if (checkedRadio) {
          answer = checkedRadio.value === 'true'
          shouldSave = true // User selected either true or false
        }
        break

      case 'SIMPLE_FILL_IN_THE_BLANK':
        // Check if there are multiple inputs (numbered) or single textarea
        const multipleInputs = this.elements.questionContainer.querySelectorAll('input[name^="answer-"]')
        if (multipleInputs.length > 0) {
          // Multiple text boxes
          answer = Array.from(multipleInputs).map(input => input.value.trim())
          shouldSave = true // Always save array structure
        } else {
          // Single textarea (legacy support)
          const textarea = this.elements.questionContainer.querySelector('textarea[name="answer"]')
          if (textarea) {
            answer = textarea.value.trim()
            shouldSave = true // Save even if empty
          }
        }
        break
        
      case 'SHORT_ANSWER':
        const textarea = this.elements.questionContainer.querySelector('textarea[name="answer"]')
        if (textarea) {
          answer = textarea.value.trim()
          shouldSave = true // Save even if empty
        }
        break

      case 'STRUCTURED_FILL_IN_THE_BLANK':
        const inputs = this.elements.questionContainer.querySelectorAll('input[name^="answer-"]')
        if (inputs.length > 0) {
          answer = Array.from(inputs).map(input => input.value.trim())
          shouldSave = true // Always save array structure
        }
        break
    }

    // Save answer for ALL modes (practice, random, test) - including boolean false
    if (shouldSave) {
      this.quiz.saveAnswer(answer)
      // Auto-save to localStorage in test mode
      if (this.quiz.mode === 'test') {
        this.quiz.saveToStorage()
      }
    }
  }

  handlePrevQuestion() {
    // Save current answer before navigating
    this.saveCurrentAnswer()
    
    if (this.quiz.prevQuestion()) {
      this.renderCurrentQuestion()
    }
  }

  handleNextQuestion() {
    // Save current answer before navigating
    this.saveCurrentAnswer()
    
    if (this.quiz.hasNextQuestion()) {
      this.quiz.nextQuestion()
      this.renderCurrentQuestion()
    } else {
      this.finishQuiz()
    }
  }
  
  // Helper method to save current answer before navigation
  saveCurrentAnswer() {
    const question = this.quiz.getCurrentQuestion()
    let answer = null
    let hasAnswer = false // Track if user actually provided an answer

    switch (question.type) {
      case 'TRUE_FALSE':
        const checkedRadio = this.elements.questionContainer.querySelector('input[name="answer"]:checked')
        if (checkedRadio) {
          answer = checkedRadio.value === 'true'
          hasAnswer = true // User selected either true or false
        }
        break

      case 'SIMPLE_FILL_IN_THE_BLANK':
        // Check if there are multiple inputs (numbered) or single textarea
        const multipleInputs = this.elements.questionContainer.querySelectorAll('input[name^="answer-"]')
        if (multipleInputs.length > 0) {
          // Multiple text boxes - save all values, even empty ones
          answer = Array.from(multipleInputs).map(input => input.value.trim())
          hasAnswer = true // Always save array structure
        } else {
          // Single textarea (legacy support)
          const textarea = this.elements.questionContainer.querySelector('textarea[name="answer"]')
          if (textarea) {
            answer = textarea.value.trim()
            hasAnswer = true // Save even if empty string
          }
        }
        break
        
      case 'SHORT_ANSWER':
        const textarea = this.elements.questionContainer.querySelector('textarea[name="answer"]')
        if (textarea) {
          answer = textarea.value.trim()
          hasAnswer = true // Save even if empty string
        }
        break

      case 'STRUCTURED_FILL_IN_THE_BLANK':
        const inputs = this.elements.questionContainer.querySelectorAll('input[name^="answer-"]')
        if (inputs.length > 0) {
          answer = Array.from(inputs).map(input => input.value.trim())
          hasAnswer = true // Always save array structure
        }
        break
    }

    // Save answer if user interacted with the question (including boolean false)
    if (hasAnswer) {
      this.quiz.saveAnswer(answer)
      // Auto-save to localStorage in test mode
      if (this.quiz.mode === 'test') {
        this.quiz.saveToStorage()
      }
    }
  }

  handleSkipQuestion() {
    this.handleNextQuestion()
  }

  handleShowAnswers(e) {
    // Check if the clicked element is the show answers button
    if (e.target.id === 'show-answers-btn') {
      const question = this.quiz.getCurrentQuestion()
      
      // CRITICAL: Save current answer before showing feedback
      this.saveCurrentAnswer()
      
      // Get the updated answer after saving
      const currentAnswer = this.quiz.getAnswer(question.id)
      
      // Re-render the current question with feedback shown
      this.elements.questionContainer.style.opacity = '0'
      
      setTimeout(() => {
        const questionElement = QuestionRenderer.render(question, currentAnswer, this.quiz.mode, true)
        this.elements.questionContainer.innerHTML = ''
        this.elements.questionContainer.appendChild(questionElement)
        
        this.elements.questionContainer.style.opacity = '1'
      }, 150)
    }
  }

  updateQuestionCounter() {
    const current = this.quiz.currentQuestionIndex + 1
    const total = this.quiz.questions.length
    this.elements.questionCounter.textContent = `${current} of ${total}`
  }

  updateProgress() {
    const progress = this.quiz.getProgress()
    this.elements.progressFill.style.width = `${progress}%`
  }

  updateNavigation() {
    this.elements.prevBtn.disabled = !this.quiz.hasPrevQuestion()
    this.elements.nextBtn.textContent = this.quiz.hasNextQuestion() ? 'Next' : 'Finish Quiz'
    
    // Update button styles based on disabled state
    this.elements.prevBtn.className = this.quiz.hasPrevQuestion() 
      ? 'btn-secondary flex items-center'
      : 'btn-secondary flex items-center opacity-50 cursor-not-allowed'
  }

  async finishQuiz() {
    // For test mode, show submission progress
    if (this.quiz.mode === 'test') {
      this.showSubmissionProgress()
    }
    
    try {
      const finalScore = await this.quiz.finish()
      this.showResults(finalScore)
      this.showScreen('results')
    } catch (error) {
      console.error('Failed to finish quiz:', error)
      // For test mode, show error and allow retry
      if (this.quiz.mode === 'test') {
        this.showSubmissionError(error.message)
      } else {
        // For practice modes, just show results without server submission
        const finalScore = this.quiz.calculateScore()
        this.showResults(finalScore)
        this.showScreen('results')
      }
    }
  }
  
  showSubmissionProgress() {
    this.elements.resultsContent.innerHTML = `
      <div class="text-center space-y-6">
        <div class="w-24 h-24 mx-auto mb-4 rounded-full bg-blue-100 flex items-center justify-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
        <h2 class="text-2xl font-bold text-gray-900">Submitting Test...</h2>
        <p class="text-gray-600">Please wait while we save your answers to the server.</p>
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-800">
          <p><strong>Important:</strong> Do not close this window or refresh the page.</p>
        </div>
      </div>
    `
    this.showScreen('results')
  }
  
  showSubmissionError(errorMessage) {
    this.elements.resultsContent.innerHTML = `
      <div class="text-center space-y-6">
        <div class="w-24 h-24 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
          <span class="text-3xl">⚠️</span>
        </div>
        <h2 class="text-2xl font-bold text-gray-900">Submission Failed</h2>
        <p class="text-gray-600">We couldn't save your test answers to the server.</p>
        <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          <p><strong>Error:</strong> ${errorMessage}</p>
        </div>
        <div class="space-y-3">
          <button id="retry-submission" class="btn-primary w-full">Try Again</button>
          <button id="continue-without-saving" class="btn-secondary w-full">Continue Without Saving</button>
        </div>
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
          <p><strong>Note:</strong> Your answers are still saved locally and can be recovered if you retry.</p>
        </div>
      </div>
    `
    
    // Add event listeners for retry buttons
    document.getElementById('retry-submission').addEventListener('click', () => {
      this.finishQuiz() // Retry submission
    })
    
    document.getElementById('continue-without-saving').addEventListener('click', () => {
      const finalScore = this.quiz.calculateScore()
      this.showResults(finalScore)
    })
  }

  showResults(score) {
    // For test mode, show submission confirmation without scores
    if (this.quiz.mode === 'test') {
      const timeTaken = Math.round((this.quiz.endTime - this.quiz.startTime) / 1000 / 60) // minutes
      
      this.elements.resultsContent.innerHTML = `
        <div class="space-y-6">
          <div class="text-center">
            <div class="w-24 h-24 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
              <span class="text-3xl">✅</span>
            </div>
            <h2 class="text-3xl font-bold text-gray-900 mb-2">Test Submitted Successfully!</h2>
            <p class="text-gray-600">Thank you, ${this.quiz.studentName}!</p>
          </div>

          <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div class="text-center space-y-3">
              <h3 class="text-lg font-semibold text-blue-900">Test Completion Summary</h3>
              <div class="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p class="text-2xl font-bold text-blue-700">${this.quiz.answers.size}</p>
                  <p class="text-sm text-blue-600">Questions Answered</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-blue-700">${timeTaken}</p>
                  <p class="text-sm text-blue-600">Minutes Taken</p>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div class="flex items-start">
              <span class="text-lg font-bold mr-2 text-amber-700">📊</span>
              <div>
                <p class="font-semibold text-amber-800">Grading Information</p>
                <p class="text-sm text-amber-700 mt-1">Your test has been submitted and will be graded by your instructor. You will receive your results separately.</p>
              </div>
            </div>
          </div>

          <div class="text-sm text-gray-600 space-y-2">
            <p><strong>Submission ID:</strong> <span class="font-mono text-xs">${Date.now()}</span></p>
            <p><strong>Completed:</strong> ${new Date().toLocaleString()}</p>
            <p><strong>Mode:</strong> Final Exam</p>
          </div>
        </div>
      `
      
      // Hide the Review Answers button for test mode
      this.elements.reviewBtn.style.display = 'none'
      return
    }
    
    // For practice and random modes, show the Review Answers button
    this.elements.reviewBtn.style.display = 'inline-block'
    
    // For practice and random modes, show detailed scoring
    const percentage = Math.round((score / this.quiz.maxScore) * 100)
    const timeTaken = Math.round((this.quiz.endTime - this.quiz.startTime) / 1000 / 60) // minutes
    
    const gradeInfo = this.getGradeInfo(percentage)
    
    this.elements.resultsContent.innerHTML = `
      <div class="space-y-6">
        <div class="text-center">
          <div class="w-24 h-24 mx-auto mb-4 rounded-full ${gradeInfo.bgColor} flex items-center justify-center">
            <span class="text-3xl">${gradeInfo.emoji}</span>
          </div>
          <h2 class="text-3xl font-bold text-gray-900 mb-2">Quiz Completed!</h2>
          <p class="text-gray-600">Well done, ${this.quiz.studentName}!</p>
        </div>

        <div class="bg-gray-50 rounded-lg p-6">
          <div class="grid grid-cols-2 gap-4 text-center">
            <div>
              <p class="text-2xl font-bold ${gradeInfo.textColor}">${score}/${this.quiz.maxScore}</p>
              <p class="text-sm text-gray-600">Points Scored</p>
            </div>
            <div>
              <p class="text-2xl font-bold ${gradeInfo.textColor}">${percentage}%</p>
              <p class="text-sm text-gray-600">Percentage</p>
            </div>
          </div>
          
          <div class="mt-4 text-center">
            <p class="text-lg font-semibold ${gradeInfo.textColor}">${gradeInfo.grade}</p>
            <p class="text-sm text-gray-600">Time taken: ${timeTaken} minutes</p>
          </div>
        </div>

        <div class="text-sm text-gray-600 space-y-2">
          <p><strong>Questions answered:</strong> ${this.quiz.answers.size} of ${this.quiz.questions.length}</p>
          <p><strong>Mode:</strong> ${
            this.quiz.mode === 'practice' ? 'Practice Mode' : 
            this.quiz.mode === 'random' ? 'Random Practice' : 
            'Final Exam'
          }</p>
          ${this.quiz.mode === 'random' ? '<p class="text-purple-600"><strong>Note:</strong> This was a random selection of 25 questions.</p>' : ''}
        </div>
      </div>
    `
  }

  getGradeInfo(percentage) {
    if (percentage >= 90) return { grade: 'Excellent!', emoji: '🌟', bgColor: 'bg-green-100', textColor: 'text-green-600' }
    if (percentage >= 80) return { grade: 'Very Good!', emoji: '🎉', bgColor: 'bg-blue-100', textColor: 'text-blue-600' }
    if (percentage >= 70) return { grade: 'Good Job!', emoji: '👍', bgColor: 'bg-yellow-100', textColor: 'text-yellow-600' }
    if (percentage >= 60) return { grade: 'Fair', emoji: '📚', bgColor: 'bg-orange-100', textColor: 'text-orange-600' }
    return { grade: 'Keep Learning!', emoji: '💪', bgColor: 'bg-red-100', textColor: 'text-red-600' }
  }

  handleRestart() {
    location.reload()
  }

  handleStartOver() {
    const confirmStartOver = confirm(
      'Are you sure you want to start over? This will clear all your progress and answers.'
    )
    
    if (confirmStartOver) {
      this.quiz.startOver()
    }
  }
  
  async checkTestModeAvailability() {
    try {
      const response = await fetch('/api/settings/test-mode-enabled')
      if (response.ok) {
        const data = await response.json()
        const testModeRadio = document.querySelector('input[name="mode"][value="test"]')
        const testModeLabel = testModeRadio ? testModeRadio.closest('label') : null
        
        if (testModeLabel) {
          if (data.enabled) {
            // Test mode is enabled
            testModeRadio.disabled = false
            testModeLabel.classList.remove('opacity-50', 'cursor-not-allowed')
            testModeLabel.classList.add('cursor-pointer')
          } else {
            // Test mode is disabled
            testModeRadio.disabled = true
            testModeRadio.checked = false // Uncheck if selected
            testModeLabel.classList.add('opacity-50', 'cursor-not-allowed')
            testModeLabel.classList.remove('cursor-pointer')
            
            // Add disabled message
            const disabledMsg = testModeLabel.querySelector('.test-disabled-msg')
            if (!disabledMsg) {
              const msgSpan = document.createElement('span')
              msgSpan.className = 'block text-xs text-red-500 test-disabled-msg'
              msgSpan.textContent = 'Final exam is currently disabled by the teacher'
              const descSpan = testModeLabel.querySelector('.block.text-sm')
              if (descSpan) {
                descSpan.parentNode.insertBefore(msgSpan, descSpan.nextSibling)
              }
            }
            
            // If test mode was selected, switch to practice mode
            const practiceRadio = document.querySelector('input[name="mode"][value="practice"]')
            if (practiceRadio) {
              practiceRadio.checked = true
            }
          }
        }
      } else {
        console.warn('Failed to check test mode availability')
      }
    } catch (error) {
      console.error('Error checking test mode availability:', error)
    }
  }
  
  checkSavedProgress() {
    const savedProgress = localStorage.getItem('quiz-progress')
    
    if (savedProgress) {
      try {
        const data = JSON.parse(savedProgress)
        const questionNumber = (data.currentQuestionIndex || 0) + 1
        // Note: We can't show total questions without API call, so just show current progress
        
        // Show the saved progress notice
        this.elements.savedStudentName.textContent = data.studentName || 'Unknown'
        this.elements.savedQuestionNumber.textContent = questionNumber
        this.elements.totalQuestions.textContent = '?' // Will be updated when test resumes
        this.elements.savedProgressNotice.classList.remove('hidden')
        
        // Hide the regular form when showing saved progress
        this.elements.studentForm.style.opacity = '0.5'
        this.elements.studentForm.style.pointerEvents = 'none'
        
      } catch (e) {
        console.error('Failed to parse saved progress:', e)
        localStorage.removeItem('quiz-progress')
        this.elements.savedProgressNotice.classList.add('hidden')
      }
    } else {
      this.elements.savedProgressNotice.classList.add('hidden')
      this.elements.studentForm.style.opacity = '1'
      this.elements.studentForm.style.pointerEvents = 'auto'
    }
  }
  
  async handleResumeTest() {
    const savedProgress = localStorage.getItem('quiz-progress')
    
    if (savedProgress) {
      try {
        const data = JSON.parse(savedProgress)
        
        // Show loading while fetching questions
        this.showQuizLoadingState()
        
        await this.quiz.init(data.studentName, 'test')
        
        // Update the total questions in the saved progress notice now that we have the data
        this.elements.totalQuestions.textContent = this.quiz.questions.length
        
        setTimeout(() => {
          alert(`Welcome back, ${data.studentName}! Resuming your test from question ${this.quiz.currentQuestionIndex + 1} of ${this.quiz.questions.length}.`)
        }, 500)
        
        this.initQuizUI()
        this.showScreen('quiz')
        this.renderCurrentQuestion()
      } catch (e) {
        console.error('Failed to resume test:', e)
        alert('Failed to resume test. Please start a new test.')
        this.handleStartFresh()
      }
    }
  }
  
  handleStartFresh() {
    localStorage.removeItem('quiz-progress')
    this.elements.savedProgressNotice.classList.add('hidden')
    this.elements.studentForm.style.opacity = '1'
    this.elements.studentForm.style.pointerEvents = 'auto'
    
    // Reset the form to test mode since they were resuming a test
    const testModeRadio = document.querySelector('input[name="mode"][value="test"]')
    if (testModeRadio) {
      testModeRadio.checked = true
    }
  }
  
  handleReview() {
    this.showComprehensiveReview()
  }
  
  handleBackToResults() {
    this.showScreen('results')
  }
  
  handleTeacherPortal() {
    // Navigate to teacher portal page
    window.location.href = '/teacher'
  }
  
  showComprehensiveReview() {
    // Set up the review header
    this.elements.reviewStudentName.textContent = this.quiz.studentName
    
    // Set the mode indicator
    const originalMode = this.quiz.mode
    let modeText, modeClass
    switch (originalMode) {
      case 'practice':
        modeText = 'Practice Mode Review'
        modeClass = 'bg-green-100 text-green-700'
        break
      case 'random':
        modeText = 'Random Practice Review'
        modeClass = 'bg-purple-100 text-purple-700'
        break
      case 'test':
        modeText = 'Final Exam Review'
        modeClass = 'bg-blue-100 text-blue-700'
        break
      default:
        modeText = 'Quiz Review'
        modeClass = 'bg-gray-100 text-gray-700'
    }
    
    this.elements.reviewModeIndicator.textContent = modeText
    this.elements.reviewModeIndicator.className = `text-sm font-medium px-3 py-1 rounded-full ${modeClass}`
    
    // Generate the comprehensive review content
    this.generateComprehensiveReview()
    
    // Show the review screen
    this.showScreen('review')
  }
  
  generateComprehensiveReview() {
    const reviewContainer = document.createElement('div')
    reviewContainer.className = 'space-y-8'
    
    // Add a summary header
    const summaryHeader = document.createElement('div')
    summaryHeader.className = 'bg-gradient-to-r from-sky-50 to-blue-50 border border-sky-200 rounded-lg p-6 mb-8'
    
    // For test mode, don't show score information
    if (this.quiz.mode === 'test') {
      summaryHeader.innerHTML = `
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Answer Review</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-center">
          <div class="bg-white rounded-lg p-4 shadow-sm">
            <p class="text-2xl font-bold text-sky-600">${this.quiz.questions.length}</p>
            <p class="text-sm text-gray-600">Total Questions</p>
          </div>
          <div class="bg-white rounded-lg p-4 shadow-sm">
            <p class="text-2xl font-bold text-green-600">${this.quiz.answers.size}</p>
            <p class="text-sm text-gray-600">Answered</p>
          </div>
        </div>
        <div class="mt-4 text-center">
              <p class="text-sm text-amber-700"><strong>Note:</strong> Scores and correct answers are not shown in final exam mode.</p>
        </div>
      `
    } else {
      // For practice and random modes, show score information
      summaryHeader.innerHTML = `
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Complete Answer Review</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
          <div class="bg-white rounded-lg p-4 shadow-sm">
            <p class="text-2xl font-bold text-sky-600">${this.quiz.questions.length}</p>
            <p class="text-sm text-gray-600">Total Questions</p>
          </div>
          <div class="bg-white rounded-lg p-4 shadow-sm">
            <p class="text-2xl font-bold text-green-600">${this.quiz.answers.size}</p>
            <p class="text-sm text-gray-600">Answered</p>
          </div>
          <div class="bg-white rounded-lg p-4 shadow-sm">
            <p class="text-2xl font-bold text-purple-600">${Math.round((this.quiz.score / this.quiz.maxScore) * 100)}%</p>
            <p class="text-sm text-gray-600">Score</p>
          </div>
        </div>
      `
    }
    
    reviewContainer.appendChild(summaryHeader)
    
    // Add all questions with answers
    this.quiz.questions.forEach((question, index) => {
      const questionCard = this.createReviewQuestionCard(question, index)
      reviewContainer.appendChild(questionCard)
    })
    
    // Clear existing content and append new review
    this.elements.reviewContent.innerHTML = ''
    this.elements.reviewContent.appendChild(reviewContainer)
  }
  
  createReviewQuestionCard(question, index) {
    const card = document.createElement('div')
    card.className = 'bg-white border border-gray-200 rounded-lg shadow-sm p-6'
    
    // Question number and header
    const questionHeader = document.createElement('div')
    questionHeader.className = 'flex items-start justify-between mb-4'
    questionHeader.innerHTML = `
      <div class="flex items-center space-x-3">
        <span class="bg-sky-100 text-sky-700 px-3 py-1 rounded-full text-sm font-bold">Q${index + 1}</span>
        <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-medium">
          ${question.type.replace(/_/g, ' ')}
        </span>
      </div>
      <span class="text-sm text-gray-600 font-medium">${question.points} point${question.points !== 1 ? 's' : ''}</span>
    `
    card.appendChild(questionHeader)
    
    // Question text
    const questionText = document.createElement('h3')
    questionText.className = 'text-lg font-semibold text-gray-900 mb-4'
    questionText.textContent = question.question_text
    card.appendChild(questionText)
    
    // Citation if available
    if (question.citation) {
      const citation = document.createElement('p')
      citation.className = 'text-sm text-gray-500 mb-4 italic'
      citation.textContent = question.citation
      card.appendChild(citation)
    }
    
    // User's answer section
    const userAnswer = this.quiz.getAnswer(question.id)
    const answerSection = this.createReviewAnswerSection(question, userAnswer)
    card.appendChild(answerSection)
    
    // Correct answer section (for practice and random modes)
    if (this.quiz.mode === 'practice' || this.quiz.mode === 'random') {
      const correctAnswerSection = this.createReviewCorrectAnswerSection(question, userAnswer)
      card.appendChild(correctAnswerSection)
    }
    
    return card
  }
  
  createReviewAnswerSection(question, userAnswer) {
    const section = document.createElement('div')
    section.className = 'mb-4'
    
    const header = document.createElement('h4')
    header.className = 'text-sm font-semibold text-gray-700 mb-2'
    header.textContent = 'Your Answer:'
    section.appendChild(header)
    
    const answerDisplay = document.createElement('div')
    answerDisplay.className = 'bg-gray-50 border border-gray-200 rounded-lg p-3'
    
    if (!userAnswer || (Array.isArray(userAnswer) && userAnswer.every(a => !a || !a.trim()))) {
      // No answer provided
      answerDisplay.className = 'bg-red-50 border border-red-200 rounded-lg p-3'
      answerDisplay.innerHTML = `
        <div class="flex items-center text-red-700">
          <span class="mr-2">⚠</span>
          <span class="text-sm font-medium">No answer provided</span>
        </div>
      `
    } else {
      // Display the answer based on question type
      this.displayUserAnswerInReview(answerDisplay, question, userAnswer)
    }
    
    section.appendChild(answerDisplay)
    return section
  }
  
  displayUserAnswerInReview(container, question, userAnswer) {
    switch (question.type) {
      case 'TRUE_FALSE':
        container.innerHTML = `
          <div class="flex items-center">
            <span class="text-lg font-medium text-gray-900">${userAnswer ? 'True' : 'False'}</span>
          </div>
        `
        break
        
      case 'SIMPLE_FILL_IN_THE_BLANK':
        if (Array.isArray(userAnswer)) {
          const answersHTML = userAnswer.map((answer, index) => 
            `<div class="mb-2"><strong>${index + 1}.</strong> ${answer || '<em class="text-gray-500">(empty)</em>'}</div>`
          ).join('')
          container.innerHTML = `<div class="space-y-1">${answersHTML}</div>`
        } else {
          container.innerHTML = `<p class="text-gray-900">${userAnswer}</p>`
        }
        break
        
      case 'STRUCTURED_FILL_IN_THE_BLANK':
        if (Array.isArray(userAnswer)) {
          const answersHTML = question.parts.map((part, index) => 
            `<div class="mb-3 p-2 bg-white rounded border">
              <div class="text-sm font-medium text-gray-600 mb-1">${part.prompt}</div>
              <div class="text-gray-900">${userAnswer[index] || '<em class="text-gray-500">(empty)</em>'}</div>
            </div>`
          ).join('')
          container.innerHTML = `<div class="space-y-2">${answersHTML}</div>`
        }
        break
        
      case 'SHORT_ANSWER':
        container.innerHTML = `
          <div class="bg-white rounded border p-3 max-h-32 overflow-y-auto">
            <p class="text-gray-900 whitespace-pre-wrap">${userAnswer}</p>
          </div>
        `
        break
    }
  }
  
  createReviewCorrectAnswerSection(question, userAnswer) {
    const section = document.createElement('div')
    section.className = 'border-t border-gray-200 pt-4'
    
    const header = document.createElement('h4')
    header.className = 'text-sm font-semibold text-gray-700 mb-2'
    header.textContent = 'Correct Answer:'
    section.appendChild(header)
    
    const correctDisplay = document.createElement('div')
    
    // Determine if the answer is correct and style accordingly
    const isCorrect = this.quiz.isAnswerCorrect(question, userAnswer)
    correctDisplay.className = isCorrect 
      ? 'bg-green-50 border border-green-200 rounded-lg p-3'
      : 'bg-red-50 border border-red-200 rounded-lg p-3'
    
    this.displayCorrectAnswerInReview(correctDisplay, question, isCorrect)
    
    section.appendChild(correctDisplay)
    return section
  }
  
  displayCorrectAnswerInReview(container, question, isCorrect) {
    const statusIcon = isCorrect ? '✓' : '✗'
    const statusText = isCorrect ? 'Correct' : 'Incorrect'
    const statusColor = isCorrect ? 'text-green-700' : 'text-red-700'
    
    switch (question.type) {
      case 'TRUE_FALSE':
        const correctAnswer = question.correct_answer ? 'True' : 'False'
        container.innerHTML = `
          <div class="flex items-start">
            <span class="text-lg font-bold mr-2 ${statusColor}">${statusIcon}</span>
            <div>
              <p class="font-semibold ${statusColor}">${statusText}</p>
              ${!isCorrect ? `<p class="text-sm mt-1">Correct answer: <strong>${correctAnswer}</strong></p>` : ''}
            </div>
          </div>
        `
        break
        
      case 'SIMPLE_FILL_IN_THE_BLANK':
        container.innerHTML = `
          <div class="flex items-start">
            <span class="text-lg font-bold mr-2 ${statusColor}">${statusIcon}</span>
            <div>
              <p class="font-semibold ${statusColor}">${statusText}</p>
              <p class="text-sm mt-1">Accepted answers: <strong>${question.correct_answers.join(', ')}</strong></p>
            </div>
          </div>
        `
        break
        
      case 'STRUCTURED_FILL_IN_THE_BLANK':
        const partsHTML = question.parts.map((part, index) => 
          `<div class="mb-2 p-2 bg-white rounded border">
            <div class="text-sm font-medium text-gray-600 mb-1">${part.prompt}</div>
            <div><strong>${part.correct_answer}</strong></div>
          </div>`
        ).join('')
        container.innerHTML = `
          <div class="flex items-start">
            <span class="text-lg font-bold mr-2 ${statusColor}">${statusIcon}</span>
            <div class="flex-1">
              <p class="font-semibold ${statusColor} mb-2">${statusText}</p>
              <div class="space-y-2">${partsHTML}</div>
            </div>
          </div>
        `
        break
        
      case 'SHORT_ANSWER':
        container.innerHTML = `
          <div class="flex items-start">
            <span class="text-lg font-bold mr-2 text-blue-700">ℹ️</span>
            <div>
              <p class="font-semibold text-blue-700">Requires Manual Grading</p>
              <p class="text-sm mt-1 text-blue-600">Short answer questions need to be reviewed manually for proper grading.</p>
              ${question.grading_notes ? `<p class="text-sm mt-2 text-gray-600"><strong>Grading Notes:</strong> ${question.grading_notes}</p>` : ''}
            </div>
          </div>
        `
        break
    }
  }
}

// Initialize App
const quiz = new QuizState()
const ui = new UIController(quiz)

// Check test mode availability and show welcome screen
setTimeout(async () => {
  await ui.checkTestModeAvailability()
  ui.showScreen('welcome')
}, 1000)
