import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { WorkoutProvider } from './context/WorkoutContext';

// Import pages
import Home from './pages/Home';
import Workout from './pages/Workout';
import AI from './pages/AI';
import Analysis from './pages/Analysis';
import Survey from './pages/Survey';

// Import components
import Navbar from './components/Navbar';

function App() {
  return (
    <WorkoutProvider>
      <Router>
        <div className="min-h-screen bg-gray-100">
          <Navbar />
          <main className="container mx-auto px-4 py-6">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/workout" element={<Workout />} />
              <Route path="/ai" element={<AI />} />
              <Route path="/analysis" element={<Analysis />} />
              <Route path="/survey" element={<Survey />} />
            </Routes>
          </main>
        </div>
      </Router>
    </WorkoutProvider>
  );
}

export default App;