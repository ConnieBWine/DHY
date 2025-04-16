import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

// Create the workout context
export const WorkoutContext = createContext();

export const WorkoutProvider = ({ children }) => {
  // State for user profile and workout plans
  const [userProfile, setUserProfile] = useState(null);
  const [workoutPlan, setWorkoutPlan] = useState(null);
  const [activeExercise, setActiveExercise] = useState(null);
  const [exerciseList, setExerciseList] = useState([]);
  const [sessionStats, setSessionStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available exercises on initial load
  useEffect(() => {
    const fetchExercises = async () => {
      try {
        const response = await axios.get('/api/exercises');
        setExerciseList(response.data.exercises);
      } catch (err) {
        console.error('Error fetching exercises:', err);
        // Fallback to hardcoded list if API fails
        setExerciseList([
          { name: 'Squat', type: 'reps' },
          { name: 'Bicep Curl', type: 'reps' },
          { name: 'Pushup', type: 'reps' },
          { name: 'Lunge', type: 'reps' },
          { name: 'Shoulder Press', type: 'reps' },
          { name: 'Plank', type: 'timed' },
          { name: 'Jumping Jack', type: 'timed' }
        ]);
      }
    };

    fetchExercises();
  }, []);

  // Function to generate a workout plan based on survey data
  const generateWorkoutPlan = async (surveyData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/workout-plan', surveyData);
      setWorkoutPlan(response.data);
      return response.data;
    } catch (err) {
      console.error('Error generating workout plan:', err);
      setError('Failed to generate workout plan. Please try again.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Function to generate a workout plan with a custom prompt
  const generateCustomWorkoutPlan = async (prompt) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/workout-prompt', { prompt });
      setWorkoutPlan(response.data.workout_plan);
      return response.data;
    } catch (err) {
      console.error('Error with custom workout prompt:', err);
      setError('Failed to process your prompt. Please try again.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Function to start tracking an exercise
  const startExercise = async (exercise, targetReps = 0, targetSets = 1, targetDuration = 0) => {
    setLoading(true);
    setError(null);
    
    try {
      const exerciseData = {
        exercise,
        target_reps: targetReps,
        target_sets: targetSets,
        target_duration: targetDuration
      };
      
      await axios.post('/api/start-exercise', exerciseData);
      
      setActiveExercise({
        name: exercise,
        targetReps,
        targetSets,
        targetDuration,
        currentReps: 0,
        currentSet: 1,
        isTimed: exerciseList.find(e => e.name.toLowerCase() === exercise.toLowerCase())?.type === 'timed'
      });
      
      return true;
    } catch (err) {
      console.error('Error starting exercise:', err);
      setError('Failed to start exercise tracking. Please try again.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Function to update session stats
  const updateSessionStats = (stats) => {
    setSessionStats(prevStats => ({
      ...prevStats,
      ...stats
    }));
  };

  // Clear current workout data
  const clearWorkout = () => {
    setActiveExercise(null);
  };

  // Provide the context values
  const contextValue = {
    userProfile,
    setUserProfile,
    workoutPlan,
    setWorkoutPlan,
    activeExercise,
    setActiveExercise,
    exerciseList,
    sessionStats,
    loading,
    error,
    generateWorkoutPlan,
    generateCustomWorkoutPlan,
    startExercise,
    updateSessionStats,
    clearWorkout
  };

  return (
    <WorkoutContext.Provider value={contextValue}>
      {children}
    </WorkoutContext.Provider>
  );
};