import fetch from 'node-fetch'

const SERVER_URL = 'http://localhost:3002'

// Test simple submission with minimal data
const testSubmission = async () => {
  try {
    console.log('🧪 Testing quick submission...')
    
    const submissionData = {
      studentName: "Test Student",
      startTime: new Date(Date.now() - 5 * 60000).toISOString(), // 5 minutes ago
      endTime: new Date().toISOString(),
      totalQuestions: 2,
      answers: [
        {
          questionId: "q1_sin_definitions",
          answer: ["Test answer 1", "Test answer 2"],
          timestamp: new Date().toISOString(),
          questionIndex: 0
        },
        {
          questionId: "q12_spiritual_gifts",
          answer: "This is my test answer for spiritual gifts",
          timestamp: new Date().toISOString(),
          questionIndex: 1
        }
      ]
    }

    const response = await fetch(`${SERVER_URL}/api/submit-test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(submissionData)
    })

    if (response.ok) {
      const result = await response.json()
      console.log('✅ Test submission successful:', result)
      console.log(`📊 Auto Score: ${result.autoScore}`)
      console.log(`📝 Questions processed: ${result.totalQuestions}`)
    } else {
      const error = await response.text()
      console.error('❌ Submission failed:', response.status, error)
    }

  } catch (error) {
    console.error('❌ Test error:', error.message)
  }
}

// Run the test
testSubmission()
