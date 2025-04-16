import React, { useContext } from 'react';
import { Link } from 'react-router-dom';
import { WorkoutContext } from '../context/WorkoutContext';
import WorkoutPlan from '../components/WorkoutPlan';

const Home = () => {
  const { workoutPlan, exerciseList } = useContext(WorkoutContext);

  return (
    <div className="space-y-8">
      {/* Hero section */}
      <div className="bg-gradient-to-r from-primary-600 to-secondary-600 rounded-xl text-white p-8 shadow-lg">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          AI-Powered Workout Tracking
        </h1>
        <p className="text-lg md:text-xl mb-6 max-w-2xl">
          Track your exercise form in real-time, get instant feedback, and improve your workout efficiency with computer vision technology.
        </p>
        <div className="flex flex-wrap gap-4">
          <Link to="/workout" className="btn bg-white text-primary-600 hover:bg-gray-100">
            Start Workout
          </Link>
          <Link to="/survey" className="btn bg-transparent border border-white text-white hover:bg-white/10">
            Create Workout Plan
          </Link>
        </div>
      </div>

      {/* Features section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card card-hover">
          <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">Real-time Tracking</h2>
          <p className="text-gray-600">
            Get instant feedback on your exercise form with advanced pose detection technology.
          </p>
        </div>

        <div className="card card-hover">
          <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">AI Workout Plans</h2>
          <p className="text-gray-600">
            Get personalized workout plans based on your fitness level, goals, and available equipment.
          </p>
        </div>

        <div className="card card-hover">
          <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">Track Progress</h2>
          <p className="text-gray-600">
            Monitor your progress, identify common form issues, and improve your technique over time.
          </p>
        </div>
      </div>

      {/* Available exercises section */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Available Exercises</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {exerciseList.map((exercise, index) => (
            <Link 
              key={index}
              to="/workout"
              className="card card-hover p-4 text-center"
            >
              <div className="font-bold mb-1">{exercise.name}</div>
              <div className="text-sm text-gray-500">
                {exercise.type === 'reps' ? 'Rep-based' : 'Time-based'}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Current workout plan section */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Current Workout Plan</h2>
        <WorkoutPlan workoutPlan={workoutPlan} />
      </div>
    </div>
  );
};

export default Home;