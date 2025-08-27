# Living Life Quiz Application

An interactive quiz application for the Living Life Bible Study course with test submission capability.

## Features

- **Multiple Quiz Modes**:
  - **Practice Mode**: Full question bank with immediate feedback and correct answers
  - **Random Practice**: 25 random questions with immediate feedback
  - **Test Mode**: Full question bank without feedback, submits answers to server

- **Question Types Supported**:
  - True/False questions
  - Simple fill-in-the-blank (single or multiple answers)
  - Structured fill-in-the-blank with multiple parts
  - Short answer questions

- **Test Mode Features**:
  - Progress saving and resumption
  - Server submission with retry logic and exponential backoff
  - SQLite database storage for submitted answers
  - Concurrency handling for multiple simultaneous submissions

- **UI Features**:
  - Responsive design with Tailwind CSS
  - Progress tracking and question navigation
  - Answer persistence across page refreshes (test mode)
  - Visual feedback and validation

## Setup and Installation

### Prerequisites

- Node.js (version 18 or higher)
- yarn package manager
- Docker (for containerized deployment)

### Quick Start with Docker (Recommended)

```bash
# Login to Azure Container Registry (one-time setup)
yarn docker:login

# Build and run locally
yarn docker:run
```

The application will be available at `http://localhost:3000`

### Local Development Setup

1. Clone or download the project files
2. Install dependencies:
   ```bash
   yarn install
   ```

### Running the Application

#### Development Mode (Frontend Only)
For development with hot reload:
```bash
yarn dev
```
This runs the Vite development server on `http://localhost:5173`

#### Production Server (Full Application)
To run the complete application with server-side test submission:

1. Build the frontend:
   ```bash
   yarn build
   ```

2. Start the server:
   ```bash
   yarn server
   ```

3. Access the application at `http://localhost:3000`

#### Development Server Mode
For server development with auto-restart:
```bash
yarn server:dev
```

## Docker Commands

- `yarn docker:login` - Login to Azure Container Registry
- `yarn docker:build` - Build Docker image locally
- `yarn docker:run` - Build and run container locally for testing
- `yarn docker:publish` - Build, tag, and push images to ACR

## File Structure

```
├── index.html              # Main HTML file
├── src/
│   ├── main.js             # Main application logic
│   └── style.css           # Styles
├── questions-master.json   # Practice mode questions (with answers)
├── questions-test.json     # Test mode questions (no answers)
├── server.js              # Express server for test submissions
├── package.json           # Dependencies and scripts
└── README.md              # This file
```

## Usage

### For Students

1. **Starting a Quiz**:
   - Enter your name
   - Select your preferred mode:
     - **Practice**: Complete question bank with feedback
     - **Random Practice**: 25 random questions with feedback
     - **Test**: Complete question bank, answers submitted to instructor

2. **Taking the Quiz**:
   - Answer questions using the provided input fields
   - Use navigation buttons to move between questions
   - In practice modes, use "Show Correct Answers" for immediate feedback
   - Progress is automatically saved in test mode

3. **Test Mode Specifics**:
   - Answers are automatically saved as you type
   - You can safely close and reopen the browser - progress will be restored
   - When finished, answers are submitted to the server automatically
   - Retry mechanism handles network issues automatically

### For Instructors

#### Accessing Submitted Tests

The server provides several API endpoints for accessing submitted test data:

1. **Recent Submissions**:
   ```
   GET /api/submissions/recent?limit=20
   ```

2. **Submission Statistics**:
   ```
   GET /api/submissions/stats
   ```

3. **Health Check**:
   ```
   GET /api/health
   ```

#### Database Structure

Test submissions are stored in SQLite database (`test_submissions.db`) with two main tables:

- **submissions**: Main submission records with student info and metadata
- **answers**: Individual answers linked to submissions

You can query the database directly using any SQLite tool or client.

## Configuration

### Environment Variables

- `PORT`: Server port (default: 3000)

### Database

The SQLite database file (`test_submissions.db`) is created automatically when the server starts. It includes:

- Automatic table creation
- Transaction support for data consistency
- Foreign key relationships
- Proper indexing for performance

## API Documentation

### POST /api/submit-test

Accepts test submissions from the client.

**Request Body**:
```json
{
  "studentName": "John Doe",
  "startTime": "2023-01-01T10:00:00.000Z",
  "endTime": "2023-01-01T11:30:00.000Z",
  "totalQuestions": 20,
  "answers": [
    {
      "questionId": "q1_sin_definitions",
      "answer": true,
      "timestamp": "2023-01-01T10:05:00.000Z",
      "questionIndex": 0
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "submissionId": 123,
  "message": "Test submission received for John Doe",
  "answersProcessed": 15
}
```

## Troubleshooting

### Common Issues

1. **Server won't start**: Make sure all dependencies are installed (`npm install`)
2. **Database errors**: Check file permissions in the project directory
3. **Test submission fails**: Check network connection and server logs
4. **Build failures**: Ensure Node.js version is 14 or higher

### Server Logs

The server provides detailed logging for:
- Database operations
- Test submissions
- Error conditions
- Connection status

### Client-Side Retry

The application automatically retries failed test submissions with exponential backoff:
- Initial retry: 1 second delay
- Second retry: 2 seconds delay  
- Third retry: 4 seconds delay
- Maximum delay: 10 seconds

## Security Considerations

- Input validation on both client and server
- SQL injection prevention using prepared statements
- Request size limits to prevent abuse
- Graceful error handling without exposing internals

---

## Question Types Specification

Question Class Schema

Below is a JSON Schema definition for a generic Question class and its different types. This schema allows you to structure your question data, ensuring consistency and making it easier for your website to parse and score.
Note: The JSON Schema syntax itself, and the use of discriminator for type differentiation, are concepts external to the provided source material but are standard practices for defining structured data schemas.

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Question Schema",
  "description": "Schema for various question types in a quiz system based on the LLBS document.",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier for the question. E.g., 'q1_sin_definitions'."
    },
    "type": {
      "type": "string",
      "description": "The type of question.",
      "enum": [
        "SIMPLE_FILL_IN_THE_BLANK",
        "STRUCTURED_FILL_IN_THE_BLANK",
        "TRUE_FALSE",
        "SHORT_ANSWER"
      ]
    },
    "question_text": {
      "type": "string",
      "description": "The main text or prompt of the question."
    },
    "points": {
      "type": "integer",
      "description": "Total points awarded for correctly answering this question. This is defined per question number in the source."
    },
    "citation": {
      "type": "string",
      "description": "Optional biblical citation for the question, if provided in the source."
    }
  },
  "required": ["id", "type", "question_text", "points"],
  "discriminator": {
    "propertyName": "type",
    "mapping": {
      "SIMPLE_FILL_IN_THE_BLANK": "#/definitions/SimpleFillInTheBlankQuestion",
      "STRUCTURED_FILL_IN_THE_BLANK": "#/definitions/StructuredFillInTheBlankQuestion",
      "TRUE_FALSE": "#/definitions/TrueFalseQuestion",
      "SHORT_ANSWER": "#/definitions/ShortAnswerQuestion"
    }
  },
  "definitions": {
    "SimpleFillInTheBlankQuestion": {
      "type": "object",
      "description": "A question where the user fills in one or more blanks directly related to the main question text. Answers are typically short and listed.",
      "properties": {
        "type": { "const": "SIMPLE_FILL_IN_THE_BLANK" },
        "correct_answers": {
          "type": "array",
          "items": { "type": "string" },
          "description": "A list of expected correct answers. The order matters if the question implicitly or explicitly lists items (e.g., 'first, second, third definition')."
        }
      },
      "required": ["correct_answers"]
    },
    "StructuredFillInTheBlankQuestion": {
      "type": "object",
      "description": "A question that acts as a header for multiple sub-parts, each with its own prompt and requiring a specific short answer.",
      "properties": {
        "type": { "const": "STRUCTURED_FILL_IN_THE_BLANK" },
        "parts": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "prompt": { "type": "string", "description": "The specific sub-prompt or question for this part (e.g., '1. How many books...')." },
              "correct_answer": { "type": "string", "description": "The correct answer for this specific sub-part." },
              "citation": { "type": "string", "description": "Optional biblical citation specific to this sub-part." }
            },
            "required": ["prompt", "correct_answer"]
          },
          "description": "An array of individual sub-questions or facts that make up this structured question."
        }
      },
      "required": ["parts"]
    },
    "TrueFalseQuestion": {
      "type": "object",
      "description": "A question requiring a 'True' or 'False' answer.",
      "properties": {
        "type": { "const": "TRUE_FALSE" },
        "correct_answer": {
          "type": "boolean",
          "description": "The correct answer: `true` for 'T', `false` for 'F'."
        }
      },
      "required": ["correct_answer"]
    },
    "ShortAnswerQuestion": {
      "type": "object",
      "description": "A question requiring a subjective or open-ended text answer, typically requiring manual grading.",
      "properties": {
        "type": { "const": "SHORT_ANSWER" },
        "grading_notes": {
          "type": "string",
          "description": "Notes for how this question should be graded, e.g., 'Requires manual review; points for thoughtful, relevant answer.'"
        }
      }
    }
  }
}
Examples of Question Data using the Schema
Here are examples of how questions from your source material would be represented using this schema:

1. Simple Fill in the Blank Question Example
• Source: "1. Write down the three definitions of sin found in the New Testament. (3 pts.) 1. Lawlessness 2. Knowing the good we ought to do and are not doing it 3. Everything that doesn’t come from faith"
{
  "id": "q1_sin_definitions",
  "type": "SIMPLE_FILL_IN_THE_BLANK",
  "question_text": "Write down the three definitions of sin found in the New Testament.",
  "points": 3,
  "correct_answers": [
    "Lawlessness",
    "Knowing the good we ought to do and are not doing it",
    "Everything that doesn’t come from faith"
  ]
}

2. Structured Fill in the Blank Question Example
• Source: "3. In regards to the books of the Bible: (4 pts.) 1. How many books are in the Old Testament? 39 books 2. How many books are in the New Testament? 27 books 3. When was the Old Testament completed? 400 BC 4. When was the New Testament completed? AD 90"
{
  "id": "q3_bible_books_details",
  "type": "STRUCTURED_FILL_IN_THE_BLANK",
  "question_text": "In regards to the books of the Bible:",
  "points": 4,
  "parts": [
    {
      "prompt": "1. How many books are in the Old Testament?",
      "correct_answer": "39 books"
    },
    {
      "prompt": "2. How many books are in the New Testament?",
      "correct_answer": "27 books"
    },
    {
      "prompt": "3. When was the Old Testament completed?",
      "correct_answer": "400 BC"
    },
    {
      "prompt": "4. When was the New Testament completed?",
      "correct_answer": "AD 90"
    }
  ]
}

3. True/False Question Example
• Source: "(T) The most important thing in Christian life is having the right relationship with God and neighbors. (Matthew 22: 34-40)"
{
  "id": "tf1_relationship_importance",
  "type": "TRUE_FALSE",
  "question_text": "The most important thing in Christian life is having the right relationship with God and neighbors.",
  "points": 1,
  "correct_answer": true,
  "citation": "Matthew 22: 34-40"
}
4. Short Answer Question Example
• Source: "12. Write down what you think your spiritual gifts are and why. (1 pt.)"
{
  "id": "q12_spiritual_gifts",
  "type": "SHORT_ANSWER",
  "question_text": "Write down what you think your spiritual gifts are and why.",
  "points": 1,
  "grading_notes": "This question requires manual review. Points may be awarded for a thoughtful, relevant answer."
}
This schema provides a flexible and structured way to represent the various question formats found in your source document, which should facilitate the design and implementation of your scoring website.