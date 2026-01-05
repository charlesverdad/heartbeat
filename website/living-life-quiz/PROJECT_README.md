# Living Life Bible Study - Student Portal

A modern, interactive quiz platform built for students to test their knowledge on Christian living and biblical studies. Features practice mode with instant feedback and final exam mode with teacher grading capabilities.

## Features

### 🎯 Quiz Modes
- **Practice Mode**: 25 random questions with immediate feedback and correct answers shown
- **Final Exam**: All questions with teacher grading and results provided separately

### 📝 Question Types Supported
- **True/False**: Binary choice questions with citation references
- **Simple Fill-in-the-Blank**: Short answer questions with multiple correct answers
- **Structured Fill-in-the-Blank**: Multi-part questions with individual prompts
- **Short Answer**: Open-ended essay questions for manual grading

### 🎨 Modern UI/UX
- Responsive design that works on all devices
- Smooth animations and transitions
- Progress tracking and navigation
- Clean, professional styling with Tailwind CSS

### ⚡ Technical Features
- Built with modern ES6+ JavaScript modules
- Vite for fast development and optimized builds
- Real-time answer saving and validation
- Comprehensive scoring system
- Review functionality
- Teacher portal for grading and management
- Docker containerization for easy deployment
- SQLite database with automatic initialization

## Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Login to Azure Container Registry (one-time setup)
yarn docker:login

# Build and run locally
yarn docker:run

# Or use Docker Compose
docker-compose up -d
```

### Option 2: Local Development

#### Prerequisites
- Node.js (version 18 or higher)
- yarn package manager

#### Installation

1. **Install dependencies**:
   ```bash
   yarn install
   ```

2. **Initialize database**:
   ```bash
   yarn init-db
   ```

3. **Start development server**:
   ```bash
   # For frontend development with hot reload
   yarn dev
   
   # For full application with server
   yarn server:dev
   ```

4. **Open your browser** to `http://localhost:5173` (dev) or `http://localhost:3000` (full app)

### Building for Production

```bash
# Build frontend for production
yarn build

# Start production server
yarn server
```

## Project Structure

```
living-life-quiz/
├── src/
│   ├── main.js              # Main frontend application logic
│   └── style.css            # Global styles and Tailwind directives
├── server/
│   ├── server.js            # Backend Express server
│   ├── init-db.js           # Database initialization script
│   └── package.json         # Server dependencies
├── public/
│   └── Heartbeat_Brandmark_Horizontal_Black.svg  # Church logo
├── questions-master.json    # Master quiz questions data
├── test-config.json         # Test mode configuration
├── index.html              # Student portal HTML
├── teacher.html            # Teacher portal HTML
├── favicon.svg             # Application favicon
├── package.json            # Frontend dependencies and scripts
├── vite.config.js          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── postcss.config.js       # PostCSS configuration
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose setup
├── docker-entrypoint.sh    # Container initialization script
├── living-life-quiz        # Docker build script
└── .dockerignore           # Docker build exclusions
```

## Usage

### For Students

1. **Enter Your Name**: Provide your full name on the welcome screen
2. **Choose Mode**: 
   - Select "Practice Mode" for 25 random questions with immediate feedback
   - Select "Final Exam" for a formal assessment graded by the teacher
3. **Take the Quiz**: Navigate through questions using Previous/Next buttons
4. **View Results**: 
   - Practice Mode: See your score, percentage, and grade immediately
   - Final Exam: Receive confirmation of submission, grades provided separately

### For Teachers

1. **Access Teacher Portal**: Navigate to `/teacher` endpoint
2. **Login**: Use the configured teacher password
3. **View Submissions**: See all student final exam submissions
4. **Grade Answers**: Review and grade student responses
5. **Manage Settings**: Enable/disable final exam mode for students

### Question Navigation
- **Previous/Next**: Navigate between questions
- **Skip**: Skip current question (can return later)
- **Auto-save**: Answers are automatically saved as you type

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `DB_PATH` | `/data/quiz_data.db` | Database file path |
| `TEACHER_PASSWORD` | `admin123` | Teacher portal password |
| `SESSION_SECRET` | `auto-generated` | Session encryption secret |
| `NODE_ENV` | `production` | Node.js environment |

### Adding Questions
Questions are stored in `questions-master.json` following the documented schema. The file supports four question types with proper validation and scoring.

### Test Configuration
Final exam questions are configured in `test-config.json` which specifies which questions from the master set should be used for the final exam.

### Customizing Styles
The application uses Tailwind CSS for styling. Modify `tailwind.config.js` to customize colors, fonts, and animations.

### Database
The application uses SQLite for data persistence:
- Student submissions and answers
- Teacher grading and feedback
- Application settings
- Automatic backups recommended for production

## Browser Compatibility

- Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Mobile responsive design
- Progressive enhancement for older browsers

## Development

### Available Scripts

#### Development Scripts
- `yarn dev` - Start frontend development server with hot reloading
- `yarn build` - Build frontend for production
- `yarn preview` - Preview production build locally
- `yarn server` - Start production server
- `yarn server:dev` - Start server with auto-restart for development
- `yarn init-db` - Initialize database tables

#### Docker Scripts
- `yarn docker:login` - Login to Azure Container Registry
- `yarn docker:build` - Build Docker image locally
- `yarn docker:run` - Build and run container locally for testing
- `yarn docker:publish` - Build, tag, and push images to ACR
- `docker-compose up -d` - Start application with Docker Compose
- `docker-compose logs -f` - View application logs

### Development Guidelines

1. **Question Types**: Each question type has its own renderer in `QuestionRenderer` class
2. **State Management**: All quiz state is managed in the `QuizState` class
3. **UI Updates**: UI updates are handled by the `UIController` class
4. **Styling**: Use Tailwind utility classes, define custom components in CSS when needed
5. **Database**: SQLite with ES6 modules, async/await patterns for database operations
6. **API Design**: RESTful endpoints with proper error handling and validation

## Deployment

### Docker (Recommended)

The application is containerized for easy deployment:

```bash
# Build and deploy
./living-life-quiz
docker-compose up -d
```

### Traditional Server

For traditional server deployment:

1. Build the frontend: `npm run build`
2. Install server dependencies: `cd server && npm ci --production`
3. Initialize database: `npm run init-db`
4. Start server: `npm start`

### Production Considerations

- Set strong `TEACHER_PASSWORD`
- Configure `SESSION_SECRET` for security
- Use HTTPS with reverse proxy (nginx/Apache)
- Regular database backups
- Monitor application logs
- Configure firewall rules

## License

MIT License - feel free to use this project for educational purposes.
