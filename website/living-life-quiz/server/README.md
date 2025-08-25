# Living Life Quiz Server

Backend server for the Living Life Quiz application built with Express.js and SQLite.

## Features

- **Quiz Submission API**: Accepts test submissions from students
- **Automatic Grading**: Calculates scores for True/False, Fill-in-the-Blank, and Structured questions
- **Manual Grading Support**: Stores Short Answer responses for teacher review
- **SQLite Database**: Persistent storage for all quiz data
- **Teacher Readiness**: Database schema supports future teacher grading interface

## Quick Start

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Initialize Database**
   ```bash
   npm run init-db
   ```

3. **Start Server**
   ```bash
   npm start        # Production mode
   npm run dev      # Development mode with auto-restart
   ```

4. **Access Application**
   - Quiz App: http://localhost:3002/
   - Health Check: http://localhost:3002/api/health
   - Submissions API: http://localhost:3002/api/submissions

## API Endpoints

### POST /api/submit-test
Submit a completed test for grading and storage.

**Request Body:**
```json
{
  "studentName": "John Doe",
  "startTime": "2024-01-15T10:00:00.000Z",
  "endTime": "2024-01-15T10:30:00.000Z",
  "totalQuestions": 50,
  "answers": [
    {
      "questionId": "q1",
      "answer": true,
      "timestamp": "2024-01-15T10:05:00.000Z",
      "questionIndex": 0
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "submissionId": "uuid-here",
  "message": "Quiz submitted successfully",
  "autoScore": 42.5,
  "totalQuestions": 50,
  "timestamp": "2024-01-15T10:30:01.000Z"
}
```

### GET /api/health
Check server and database health status.

### GET /api/submissions
Get all quiz submissions (for future teacher interface).

## Database Schema

### quiz_submissions
- Stores overall quiz metadata
- Tracks automatic and manual scores
- Supports teacher grading workflow

### student_answers
- Individual question responses
- Automatic scoring results
- Space for manual grading and teacher feedback

### grading_log
- Audit trail for teacher grading actions
- Tracks score overrides and feedback

## Scoring Logic

- **True/False**: Full points for correct answer, 0 for incorrect
- **Simple Fill-in-the-Blank**: Partial credit for multiple answer questions
- **Structured Fill-in-the-Blank**: Partial credit per correct part
- **Short Answer**: Full points if answered (requires manual review)

## Future Enhancements

The database is designed to support:
- Teacher grading interface
- Score overrides for individual questions
- Detailed teacher feedback
- Grading audit trails
- Bulk grading operations
