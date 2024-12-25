export default {
    // Backend URL, dynamically set based on environment
    isBackend: process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000',
  
    // Default id_token for non-development environments (fallback)
    id_token: process.env.REACT_APP_ID_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjpmYWxzZSwibG9naW4iOiJ1c2VyIiwiaWF0IjoxNTczNzQ4ODI1LCJleHAiOjE2MjA0MDQ4MjV9.Jd1Trqu6izHq2R3uw4enrDlQKG4mzZdipSMdYQD_9JM',
  
    // Token expiration time (if needed for configuration)
    tokenExpirationMinutes: 30, // Can be adjusted as required
  };  