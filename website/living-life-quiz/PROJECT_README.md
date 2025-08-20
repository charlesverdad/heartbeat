# Living Life Quiz - Student Portal

A modern, interactive quiz platform built for students to test their knowledge on Christian living and biblical studies. Features both practice and test modes with instant feedback and comprehensive scoring.

## Features

### 🎯 Quiz Modes
- **Practice Mode**: Get immediate feedback on answers with correct responses shown
- **Test Mode**: Complete assessment with results shown at the end

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

## Quick Start

### Prerequisites
- Node.js (version 16 or higher)
- Yarn package manager

### Installation

1. **Install dependencies**:
   ```bash
   yarn install
   ```

2. **Start development server**:
   ```bash
   yarn dev
   ```

3. **Open your browser** to `http://localhost:3000`

### Building for Production

```bash
# Build for production
yarn build

# Preview production build
yarn preview
```

## Project Structure

```
living-life-quiz/
├── src/
│   ├── main.js          # Main application logic
│   └── style.css        # Global styles and Tailwind directives
├── public/
│   └── favicon.svg      # Application favicon
├── questions-master.json # Quiz questions data
├── index.html          # Main HTML file
├── package.json        # Dependencies and scripts
├── vite.config.js      # Vite configuration
├── tailwind.config.js  # Tailwind CSS configuration
└── postcss.config.js   # PostCSS configuration
```

## Usage

### For Students

1. **Enter Your Name**: Provide your full name on the welcome screen
2. **Choose Mode**: 
   - Select "Practice Mode" to see correct answers immediately
   - Select "Test Mode" for a formal assessment experience
3. **Take the Quiz**: Navigate through questions using Previous/Next buttons
4. **View Results**: See your score, percentage, and grade at completion

### Question Navigation
- **Previous/Next**: Navigate between questions
- **Skip**: Skip current question (can return later)
- **Auto-save**: Answers are automatically saved as you type

## Configuration

### Adding Questions
Questions are stored in `questions-master.json` following the documented schema. The file supports four question types with proper validation and scoring.

### Customizing Styles
The application uses Tailwind CSS for styling. Modify `tailwind.config.js` to customize colors, fonts, and animations.

### Environment Setup
All configuration is handled through Vite. Modify `vite.config.js` for build settings and development server options.

## Browser Compatibility

- Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Mobile responsive design
- Progressive enhancement for older browsers

## Development

### Available Scripts

- `yarn dev` - Start development server with hot reloading
- `yarn build` - Build for production
- `yarn preview` - Preview production build locally

### Development Guidelines

1. **Question Types**: Each question type has its own renderer in `QuestionRenderer` class
2. **State Management**: All quiz state is managed in the `QuizState` class
3. **UI Updates**: UI updates are handled by the `UIController` class
4. **Styling**: Use Tailwind utility classes, define custom components in CSS when needed

## License

MIT License - feel free to use this project for educational purposes.
