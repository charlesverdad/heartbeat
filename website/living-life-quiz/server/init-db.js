import sqlite3 from 'sqlite3'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const dbPath = join(__dirname, 'quiz_data.db')

// Enable verbose mode for debugging
const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Error opening database:', err.message)
    process.exit(1)
  }
  console.log('Connected to SQLite database.')
})

// Create tables
const createTables = () => {
  // Quiz submissions table - stores overall quiz metadata
  db.run(`
    CREATE TABLE IF NOT EXISTS quiz_submissions (
      id TEXT PRIMARY KEY,
      student_name TEXT NOT NULL,
      quiz_mode TEXT NOT NULL CHECK (quiz_mode IN ('practice', 'random', 'test')),
      start_time DATETIME NOT NULL,
      end_time DATETIME NOT NULL,
      total_questions INTEGER NOT NULL,
      auto_score REAL DEFAULT 0,
      manual_score REAL DEFAULT NULL,
      final_score REAL DEFAULT NULL,
      graded_by TEXT DEFAULT NULL,
      graded_at DATETIME DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `, (err) => {
    if (err) {
      console.error('Error creating quiz_submissions table:', err.message)
    } else {
      console.log('✓ Created quiz_submissions table')
    }
  })

  // Student answers table - stores individual question answers
  db.run(`
    CREATE TABLE IF NOT EXISTS student_answers (
      id TEXT PRIMARY KEY,
      submission_id TEXT NOT NULL,
      question_id TEXT NOT NULL,
      question_index INTEGER NOT NULL,
      question_type TEXT NOT NULL,
      question_text TEXT NOT NULL,
      question_points REAL NOT NULL,
      user_answer TEXT, -- JSON string for complex answers
      correct_answer TEXT, -- JSON string for correct answers (for practice/random modes)
      auto_points REAL DEFAULT 0,
      manual_points REAL DEFAULT NULL,
      final_points REAL DEFAULT NULL,
      teacher_feedback TEXT DEFAULT NULL,
      answered_at DATETIME NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (submission_id) REFERENCES quiz_submissions(id)
    )
  `, (err) => {
    if (err) {
      console.error('Error creating student_answers table:', err.message)
    } else {
      console.log('✓ Created student_answers table')
    }
  })

  // Teacher grading log - tracks manual grading actions
  db.run(`
    CREATE TABLE IF NOT EXISTS grading_log (
      id TEXT PRIMARY KEY,
      submission_id TEXT NOT NULL,
      answer_id TEXT,
      teacher_name TEXT NOT NULL,
      action TEXT NOT NULL CHECK (action IN ('grade_answer', 'override_score', 'add_feedback')),
      old_value TEXT,
      new_value TEXT,
      notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (submission_id) REFERENCES quiz_submissions(id),
      FOREIGN KEY (answer_id) REFERENCES student_answers(id)
    )
  `, (err) => {
    if (err) {
      console.error('Error creating grading_log table:', err.message)
    } else {
      console.log('✓ Created grading_log table')
    }
  })

  // Settings table - stores application settings
  db.run(`
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      description TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `, (err) => {
    if (err) {
      console.error('Error creating settings table:', err.message)
    } else {
      console.log('✓ Created settings table')
      
      // Insert default settings
      db.run(`
        INSERT OR IGNORE INTO settings (key, value, description)
        VALUES ('test_mode_enabled', 'false', 'Whether test mode is available to students')
      `, (err) => {
        if (err) {
          console.error('Error inserting default settings:', err.message)
        } else {
          console.log('✓ Inserted default settings')
        }
      })
    }
  })
}

// Create indexes for better performance
const createIndexes = () => {
  const indexes = [
    'CREATE INDEX IF NOT EXISTS idx_submissions_student ON quiz_submissions(student_name)',
    'CREATE INDEX IF NOT EXISTS idx_submissions_mode ON quiz_submissions(quiz_mode)',
    'CREATE INDEX IF NOT EXISTS idx_submissions_created ON quiz_submissions(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_answers_submission ON student_answers(submission_id)',
    'CREATE INDEX IF NOT EXISTS idx_answers_question ON student_answers(question_id)',
    'CREATE INDEX IF NOT EXISTS idx_grading_submission ON grading_log(submission_id)',
    'CREATE INDEX IF NOT EXISTS idx_grading_answer ON grading_log(answer_id)'
  ]

  indexes.forEach((indexSQL, i) => {
    db.run(indexSQL, (err) => {
      if (err) {
        console.error(`Error creating index ${i + 1}:`, err.message)
      } else {
        console.log(`✓ Created index ${i + 1}`)
      }
    })
  })
}

// Initialize database
console.log('Initializing database...')
createTables()

// Wait a bit for tables to be created, then create indexes
setTimeout(() => {
  createIndexes()
  
  // Close database connection
  setTimeout(() => {
    db.close((err) => {
      if (err) {
        console.error('Error closing database:', err.message)
      } else {
        console.log('✓ Database initialization complete!')
        console.log(`Database created at: ${dbPath}`)
      }
    })
  }, 1000)
}, 500)
