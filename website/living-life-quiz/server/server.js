import express from 'express'
import cors from 'cors'
import sqlite3 from 'sqlite3'
import { v4 as uuidv4 } from 'uuid'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { readFileSync } from 'fs'
import session from 'express-session'
import crypto from 'crypto'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const dbPath = join(__dirname, 'quiz_data.db')

const app = express()
const PORT = process.env.PORT || 3002

// Middleware
app.use(cors())
app.use(express.json({ limit: '10mb' }))

// Session configuration for teacher authentication
app.use(session({
  secret: process.env.SESSION_SECRET || crypto.randomBytes(64).toString('hex'),
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: false, // Set to true if using HTTPS
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}))

// Serve static files - prioritize built files if available, fallback to source
const distPath = join(__dirname, '../dist')
const sourcePath = join(__dirname, '../')

// Try to serve built files first, then fallback to source files
app.use(express.static(distPath))
app.use(express.static(sourcePath))

// Database connection
let db = null

const initDatabase = () => {
  return new Promise((resolve, reject) => {
    db = new sqlite3.Database(dbPath, (err) => {
      if (err) {
        console.error('Error opening database:', err.message)
        reject(err)
      } else {
        console.log('Connected to SQLite database.')
        resolve()
      }
    })
  })
}

// Helper function to calculate automatic score for a question
const calculateAutoScore = (question, userAnswer, correctAnswers) => {
  if (!userAnswer || userAnswer === '' || (Array.isArray(userAnswer) && userAnswer.every(a => !a || !a.trim()))) {
    return 0 // No answer provided
  }

  const compareStrings = (str1, str2) => {
    if (!str1 || !str2) return false
    return str1.toLowerCase().trim() === str2.toLowerCase().trim()
  }

  switch (question.question_type) {
    case 'TRUE_FALSE':
      const correctAnswer = correctAnswers.correct_answer
      return userAnswer === correctAnswer ? question.question_points : 0

    case 'SIMPLE_FILL_IN_THE_BLANK':
      if (Array.isArray(userAnswer)) {
        // Multiple answers - partial credit possible
        const correctCount = userAnswer.filter(answer => 
          answer && answer.trim() && 
          correctAnswers.correct_answers.some(correct => compareStrings(answer, correct))
        ).length
        
        // Partial credit: points distributed across all expected answers
        const pointsPerAnswer = question.question_points / correctAnswers.correct_answers.length
        return correctCount * pointsPerAnswer
      } else {
        // Single answer
        return correctAnswers.correct_answers.some(correct => compareStrings(userAnswer, correct)) 
          ? question.question_points : 0
      }

    case 'STRUCTURED_FILL_IN_THE_BLANK':
      if (!Array.isArray(userAnswer)) return 0
      const correctParts = correctAnswers.parts.filter((part, index) => 
        userAnswer[index] && compareStrings(userAnswer[index], part.correct_answer)
      ).length
      
      // Partial credit: points distributed across all parts
      const pointsPerPart = question.question_points / correctAnswers.parts.length
      return correctParts * pointsPerPart

    case 'SHORT_ANSWER':
      // Short answers always get full points if non-empty (require manual grading)
      return userAnswer && userAnswer.trim().length > 0 ? question.question_points : 0

    default:
      return 0
  }
}

// POST /api/submit-test - Submit quiz results
app.post('/api/submit-test', async (req, res) => {
  try {
    const { studentName, startTime, endTime, totalQuestions, answers } = req.body

    // Validate required fields
    if (!studentName || !startTime || !endTime || !totalQuestions || !Array.isArray(answers)) {
      return res.status(400).json({
        error: 'Missing required fields: studentName, startTime, endTime, totalQuestions, answers'
      })
    }

    // Generate submission ID
    const submissionId = uuidv4()
    
    // Read question data to get correct answers and calculate scores
    const questionsPath = join(__dirname, '../questions-master.json')
    const questionsData = JSON.parse(readFileSync(questionsPath, 'utf8'))
    const questionMap = new Map(questionsData.map(q => [q.id, q]))
    
    let autoScore = 0
    const processedAnswers = []

    // Process each answer and calculate auto score
    for (const answerData of answers) {
      const question = questionMap.get(answerData.questionId)
      if (!question) {
        console.warn(`Question not found: ${answerData.questionId}`)
        continue
      }

      const answerId = uuidv4()
      const autoPoints = calculateAutoScore(
        {
          question_type: question.type,
          question_points: question.points
        },
        answerData.answer,
        question
      )

      autoScore += autoPoints

      processedAnswers.push({
        id: answerId,
        submission_id: submissionId,
        question_id: answerData.questionId,
        question_index: answerData.questionIndex,
        question_type: question.type,
        question_text: question.question_text,
        question_points: question.points,
        user_answer: JSON.stringify(answerData.answer),
        correct_answer: JSON.stringify({
          type: question.type,
          correct_answer: question.correct_answer,
          correct_answers: question.correct_answers,
          parts: question.parts
        }),
        auto_points: autoPoints,
        final_points: autoPoints, // Initially set to auto score
        answered_at: answerData.timestamp
      })
    }

    // Insert quiz submission
    await new Promise((resolve, reject) => {
      const stmt = db.prepare(`
        INSERT INTO quiz_submissions (
          id, student_name, quiz_mode, start_time, end_time, 
          total_questions, auto_score, final_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `)

      stmt.run([
        submissionId,
        studentName,
        'test', // Only test mode submissions come through this endpoint
        startTime,
        endTime,
        totalQuestions,
        autoScore,
        autoScore // Initially final score equals auto score
      ], function(err) {
        if (err) {
          reject(err)
        } else {
          resolve(this.lastID)
        }
      })

      stmt.finalize()
    })

    // Insert student answers
    for (const answer of processedAnswers) {
      await new Promise((resolve, reject) => {
        const stmt = db.prepare(`
          INSERT INTO student_answers (
            id, submission_id, question_id, question_index, question_type,
            question_text, question_points, user_answer, correct_answer,
            auto_points, final_points, answered_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `)

        stmt.run([
          answer.id,
          answer.submission_id,
          answer.question_id,
          answer.question_index,
          answer.question_type,
          answer.question_text,
          answer.question_points,
          answer.user_answer,
          answer.correct_answer,
          answer.auto_points,
          answer.final_points,
          answer.answered_at
        ], function(err) {
          if (err) {
            reject(err)
          } else {
            resolve(this.lastID)
          }
        })

        stmt.finalize()
      })
    }

    // Return success response
    res.status(200).json({
      success: true,
      submissionId,
      message: 'Quiz submitted successfully',
      autoScore,
      totalQuestions: processedAnswers.length,
      timestamp: new Date().toISOString()
    })

    console.log(`✓ Quiz submitted: ${studentName} (${submissionId}) - Score: ${autoScore}`)

  } catch (error) {
    console.error('Error submitting quiz:', error)
    res.status(500).json({
      error: 'Failed to submit quiz',
      message: error.message
    })
  }
})

// GET /api/health - Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    database: db ? 'connected' : 'disconnected'
  })
})

// Teacher Portal Routes
const TEACHER_PASSWORD = process.env.TEACHER_PASSWORD || 'supersecret'

// Middleware to protect teacher routes
const requireAuth = (req, res, next) => {
  if (req.session && req.session.isAuthenticated) {
    next()
  } else {
    res.status(401).json({ message: 'Unauthorized' })
  }
}

// POST /api/teacher/login
app.post('/api/teacher/login', (req, res) => {
  const { password } = req.body
  if (password === TEACHER_PASSWORD) {
    req.session.isAuthenticated = true
    res.status(200).json({ message: 'Login successful' })
  } else {
    res.status(401).json({ message: 'Invalid password' })
  }
})

// POST /api/teacher/logout
app.post('/api/teacher/logout', (req, res) => {
  req.session.destroy(err => {
    if (err) {
      return res.status(500).json({ message: 'Logout failed' })
    }
    res.clearCookie('connect.sid')
    res.status(200).json({ message: 'Logout successful' })
  })
})

// GET /api/teacher/check-session
app.get('/api/teacher/check-session', requireAuth, (req, res) => {
  res.status(200).json({ message: 'Authenticated' })
})

// GET /api/teacher/submissions - Get all submissions with detailed questions for teacher grading
app.get('/api/teacher/submissions', requireAuth, async (req, res) => {
  try {
    const submissions = await new Promise((resolve, reject) => {
      db.all(`
        SELECT 
          id, student_name, start_time, end_time, total_questions, 
          auto_score, final_score, created_at as submitted_at
        FROM quiz_submissions
        ORDER BY created_at DESC
      `, (err, rows) => {
        if (err) return reject(err)
        resolve(rows)
      })
    })
    
    // For each submission, get detailed answers with question info
    for (const submission of submissions) {
      submission.questions = await new Promise((resolve, reject) => {
        db.all(`
          SELECT 
            question_id, question_type, question_text, question_points as max_points, 
            user_answer, correct_answer, auto_points, final_points as points_awarded
          FROM student_answers
          WHERE submission_id = ?
          ORDER BY question_index
        `, [submission.id], (err, rows) => {
          if (err) return reject(err)
          resolve(rows.map(row => {
            const correctAnswerData = JSON.parse(row.correct_answer)
            return {
              question_id: row.question_id,
              question_type: row.question_type,
              question_text: row.question_text,
              max_points: row.max_points,
              points_awarded: row.points_awarded,
              auto_points: row.auto_points,
              user_answer: JSON.parse(row.user_answer),
              correct_answer: correctAnswerData.correct_answer,
              correct_answers: correctAnswerData.correct_answers,
              parts: correctAnswerData.parts,
              grading_notes: null // Can add grading notes from question data if needed
            }
          }))
        })
      })
      submission.max_score = submission.questions.reduce((sum, q) => sum + q.max_points, 0)
      submission.total_score = submission.final_score
    }

    res.json({ success: true, submissions })
  } catch (error) {
    console.error('Error fetching submissions:', error)
    res.status(500).json({ error: 'Failed to fetch submissions', message: error.message })
  }
})

// POST /api/teacher/update-grade
app.post('/api/teacher/update-grade', requireAuth, async (req, res) => {
  const { submissionId, questionId, pointsAwarded } = req.body

  if (!submissionId || !questionId || pointsAwarded === undefined) {
    return res.status(400).json({ message: 'Missing required fields' })
  }

  try {
    // Update the final points for the specific question
    await new Promise((resolve, reject) => {
      db.run(
        'UPDATE student_answers SET final_points = ? WHERE submission_id = ? AND question_id = ?',
        [pointsAwarded, submissionId, questionId],
        function(err) {
          if (err) return reject(err)
          if (this.changes === 0) return reject(new Error('Answer not found'))
          resolve()
        }
      )
    })

    // Recalculate the total final score for the submission
    const { totalScore } = await new Promise((resolve, reject) => {
      db.get('SELECT SUM(final_points) as totalScore FROM student_answers WHERE submission_id = ?', 
             [submissionId], 
             (err, row) => {
        if (err) return reject(err)
        resolve(row)
      })
    })

    // Update the final score in the main submission table
    await new Promise((resolve, reject) => {
      db.run('UPDATE quiz_submissions SET final_score = ? WHERE id = ?', [totalScore, submissionId], (err) => {
        if (err) return reject(err)
        resolve()
      })
    })

    res.status(200).json({ success: true, message: 'Grade updated successfully', newTotalScore: totalScore })
  } catch (error) {
    console.error('Error updating grade:', error)
    res.status(500).json({ error: 'Failed to update grade', message: error.message })
  }
})

// GET /teacher - Serve the teacher portal
app.get('/teacher', (req, res) => {
  res.sendFile(join(__dirname, '../teacher.html'))
})

// Start server
const startServer = async () => {
  try {
    await initDatabase()
    
    app.listen(PORT, () => {
      console.log(`🚀 Quiz server running on http://localhost:${PORT}`)
      console.log(`📊 Database: ${dbPath}`)
      console.log(`🔗 Health check: http://localhost:${PORT}/api/health`)
      console.log(`📝 Submit endpoint: POST http://localhost:${PORT}/api/submit-test`)
    })
  } catch (error) {
    console.error('Failed to start server:', error)
    process.exit(1)
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down server...')
  if (db) {
    db.close((err) => {
      if (err) {
        console.error('Error closing database:', err.message)
      } else {
        console.log('✓ Database connection closed.')
      }
      process.exit(0)
    })
  } else {
    process.exit(0)
  }
})

startServer()
