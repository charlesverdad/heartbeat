const express = require('express')
const sqlite3 = require('sqlite3').verbose()
const path = require('path')
const fs = require('fs')

const app = express()
const PORT = process.env.PORT || 3000

// Middleware
app.use(express.json({ limit: '10mb' }))
app.use(express.static('.')) // Serve static files from current directory

// Initialize SQLite database
const dbPath = path.join(__dirname, 'test_submissions.db')
const db = new sqlite3.Database(dbPath)

// Create tables if they don't exist
db.serialize(() => {
  // Main submissions table
  db.run(`
    CREATE TABLE IF NOT EXISTS submissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_name TEXT NOT NULL,
      start_time TEXT NOT NULL,
      end_time TEXT NOT NULL,
      total_questions INTEGER NOT NULL,
      submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      submission_data TEXT NOT NULL
    )
  `)
  
  // Individual answers table for easier querying
  db.run(`
    CREATE TABLE IF NOT EXISTS answers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      submission_id INTEGER NOT NULL,
      question_id TEXT NOT NULL,
      question_index INTEGER NOT NULL,
      answer_value TEXT,
      answer_type TEXT,
      answered_at TEXT NOT NULL,
      FOREIGN KEY (submission_id) REFERENCES submissions (id)
    )
  `)
  
  console.log('Database initialized successfully')
})

// API endpoint to receive test submissions
app.post('/api/submit-test', async (req, res) => {
  try {
    const { studentName, startTime, endTime, totalQuestions, answers } = req.body
    
    // Validate required fields
    if (!studentName || !startTime || !endTime || !totalQuestions || !Array.isArray(answers)) {
      return res.status(400).json({
        error: 'Missing required fields',
        required: ['studentName', 'startTime', 'endTime', 'totalQuestions', 'answers']
      })
    }
    
    // Use a transaction to ensure data consistency
    db.serialize(() => {
      db.run('BEGIN TRANSACTION')
      
      try {
        // Insert main submission record
        const submissionStmt = db.prepare(`
          INSERT INTO submissions (student_name, start_time, end_time, total_questions, submission_data)
          VALUES (?, ?, ?, ?, ?)
        `)
        
        const submissionData = JSON.stringify(req.body)
        
        submissionStmt.run([studentName, startTime, endTime, totalQuestions, submissionData], function(err) {
          if (err) {
            console.error('Error inserting submission:', err)
            db.run('ROLLBACK')
            return res.status(500).json({ error: 'Failed to save submission' })
          }
          
          const submissionId = this.lastID
          
          // Insert individual answers
          const answerStmt = db.prepare(`
            INSERT INTO answers (submission_id, question_id, question_index, answer_value, answer_type, answered_at)
            VALUES (?, ?, ?, ?, ?, ?)
          `)
          
          let answersProcessed = 0
          const totalAnswers = answers.length
          
          if (totalAnswers === 0) {
            // No answers to process, just commit the submission
            db.run('COMMIT')
            return res.json({
              success: true,
              submissionId,
              message: `Test submission received for ${studentName}`,
              answersProcessed: 0
            })
          }
          
          answers.forEach((answer, index) => {
            const { questionId, answer: answerValue, timestamp, questionIndex } = answer
            
            // Determine answer type and serialize complex answers
            let serializedAnswer
            let answerType
            
            if (typeof answerValue === 'boolean') {
              serializedAnswer = answerValue.toString()
              answerType = 'boolean'
            } else if (Array.isArray(answerValue)) {
              serializedAnswer = JSON.stringify(answerValue)
              answerType = 'array'
            } else if (typeof answerValue === 'string') {
              serializedAnswer = answerValue
              answerType = 'string'
            } else {
              serializedAnswer = answerValue ? answerValue.toString() : ''
              answerType = 'other'
            }
            
            answerStmt.run([
              submissionId,
              questionId,
              questionIndex,
              serializedAnswer,
              answerType,
              timestamp
            ], (err) => {
              if (err) {
                console.error(`Error inserting answer ${index + 1}:`, err)
                db.run('ROLLBACK')
                return res.status(500).json({ error: 'Failed to save answers' })
              }
              
              answersProcessed++
              
              // If all answers are processed, commit the transaction
              if (answersProcessed === totalAnswers) {
                db.run('COMMIT')
                console.log(`Successfully saved test submission for ${studentName} with ${answersProcessed} answers`)
                
                res.json({
                  success: true,
                  submissionId,
                  message: `Test submission received for ${studentName}`,
                  answersProcessed
                })
              }
            })
          })
          
          answerStmt.finalize()
        })
        
        submissionStmt.finalize()
        
      } catch (error) {
        db.run('ROLLBACK')
        throw error
      }
    })
    
  } catch (error) {
    console.error('Error processing test submission:', error)
    res.status(500).json({
      error: 'Internal server error',
      message: 'Failed to process test submission'
    })
  }
})

// API endpoint to get submission statistics (optional)
app.get('/api/submissions/stats', (req, res) => {
  db.all(`
    SELECT 
      COUNT(*) as total_submissions,
      COUNT(DISTINCT student_name) as unique_students,
      AVG(total_questions) as avg_questions
    FROM submissions
  `, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to fetch statistics' })
    }
    res.json(rows[0])
  })
})

// API endpoint to get recent submissions (optional)
app.get('/api/submissions/recent', (req, res) => {
  const limit = req.query.limit || 10
  
  db.all(`
    SELECT 
      id,
      student_name,
      start_time,
      end_time,
      total_questions,
      submitted_at
    FROM submissions 
    ORDER BY submitted_at DESC 
    LIMIT ?
  `, [limit], (err, rows) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to fetch submissions' })
    }
    res.json(rows)
  })
})

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    database: 'connected'
  })
})

// Serve the main application
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'))
})

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err)
  res.status(500).json({ 
    error: 'Internal server error',
    message: err.message 
  })
})

// Start server
app.listen(PORT, () => {
  console.log(`Quiz server running on port ${PORT}`)
  console.log(`Database: ${dbPath}`)
  console.log(`Open http://localhost:${PORT} to access the quiz`)
})

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Received SIGTERM, closing database connection...')
  db.close((err) => {
    if (err) {
      console.error('Error closing database:', err)
    } else {
      console.log('Database connection closed')
    }
    process.exit(0)
  })
})

process.on('SIGINT', () => {
  console.log('Received SIGINT, closing database connection...')
  db.close((err) => {
    if (err) {
      console.error('Error closing database:', err)
    } else {
      console.log('Database connection closed')
    }
    process.exit(0)
  })
})
