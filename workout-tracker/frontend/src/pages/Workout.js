import React, { useState, useContext, useEffect } from 'react';
import { WorkoutContext } from '../context/WorkoutContext';
import VideoFeed from '../components/VideoFeed';
import ExerciseControls from '../components/ExerciseControls';
import WorkoutPlan from '../components/WorkoutPlan';

const Workout = () => {
  const { workoutPlan, startExercise, activeExercise, updateSessionStats } = useContext(WorkoutContext);
  
  // State for exercise data from video feed
  const [exerciseData, setExerciseData] = useState({
    rep_count: 0,
    state: 'IDLE',
    feedback: [],
    elapsed_time: 0,
    remaining_time: 0
  });
  
  // State for camera active/inactive
  const [cameraActive, setCameraActive] = useState(true);
  
  // Update stats periodically
  useEffect(() => {
    const updateStatsInterval = setInterval(() => {
      if (exerciseData && exerciseData.feedback && exerciseData.feedback.length > 0) {
        // Only update if we have feedback data
        updateSessionStats({
          latestFeedback: exerciseData.feedback
        });
      }
    }, 10000); // Update every 10 seconds
    
    return () => clearInterval(updateStatsInterval);
  }, [exerciseData, updateSessionStats]);
  
  // Handle selecting an exercise from the workout plan
  const handleSelectExercise = (exercise, targetReps, targetSets, targetDuration) => {
    startExercise(exercise, targetReps, targetSets, targetDuration);
  };
  
  // Handle changing the active exercise
  const handleExerciseChange = (exercise, targetReps, targetSets, targetDuration) => {
    if (exercise) {
      startExercise(exercise, targetReps, targetSets, targetDuration);
    } else {
      // Exercise stopped
      setCameraActive(false);
      setTimeout(() => setCameraActive(true), 500); // Brief delay to reset camera
    }
  };
  
  // Handle exercise data from video feed
  const handleExerciseData = (data) => {
    setExerciseData(data);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Workout Tracker</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main video feed and exercise controls column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Video feed */}
          <div className="card p-4">
            <VideoFeed 
              onExerciseData={handleExerciseData}
              active={cameraActive}
              selectedExercise={activeExercise?.name}
              className="w-full"
            />
          </div>
          
          {/* Exercise controls */}
          <ExerciseControls 
            onExerciseChange={handleExerciseChange}
            currentExercise={activeExercise?.name}
            exerciseData={exerciseData}
          />
        </div>
        
        {/* Workout plan column */}
        <div>
          <WorkoutPlan 
            workoutPlan={workoutPlan} 
            onSelectExercise={handleSelectExercise} 
          />
          
          {/* Exercise instructions */}
          <div className="card mt-6">
            <h2 className="text-xl font-bold mb-4">Exercise Instructions</h2>
            
            {activeExercise ? (
              <div>
                <h3 className="font-semibold text-lg mb-2">{activeExercise.name}</h3>
                
                {/* Exercise-specific instructions */}
                {activeExercise.name.toLowerCase().includes('squat') && (
                  <div className="space-y-3">
                    <p>Stand with feet shoulder-width apart, toes slightly pointing outward.</p>
                    <p>Keep your chest up, back straight, and core engaged.</p>
                    <p>Bend your knees and lower your hips as if sitting in a chair.</p>
                    <p>Go as low as comfortable, ideally until thighs are parallel to the ground.</p>
                    <p>Push through your heels to return to the starting position.</p>
                  </div>
                )}
                
                {activeExercise.name.toLowerCase().includes('curl') && (
                  <div className="space-y-3">
                    <p>Stand with feet shoulder-width apart, holding weights at your sides.</p>
                    <p>Keep elbows close to your torso and palms facing forward.</p>
                    <p>Curl the weights up toward your shoulders while keeping upper arms stationary.</p>
                    <p>Squeeze your biceps at the top of the movement.</p>
                    <p>Lower the weights back to the starting position with control.</p>
                  </div>
                )}
                
                {activeExercise.name.toLowerCase().includes('pushup') && (
                  <div className="space-y-3">
                    <p>Start in a high plank position with hands slightly wider than shoulder-width.</p>
                    <p>Keep your body in a straight line from head to heels.</p>
                    <p>Lower your chest toward the ground by bending your elbows.</p>
                    <p>Push back up to the starting position, fully extending your arms.</p>
                    <p>Keep your core engaged throughout the movement.</p>
                  </div>
                )}
                
                {activeExercise.name.toLowerCase().includes('lunge') && (
                  <div className="space-y-3">
                    <p>Stand with feet hip-width apart.</p>
                    <p>Step forward with one leg and lower your body until both knees are bent at 90 degrees.</p>
                    <p>Keep your front knee aligned with your ankle and don't let it extend past your toes.</p>
                    <p>Push through your front heel to return to the starting position.</p>
                    <p>Repeat on the other side to complete one rep.</p>
                  </div>
                )}
                
                {activeExercise.name.toLowerCase().includes('plank') && (
                  <div className="space-y-3">
                    <p>Start in a forearm plank position with elbows directly under shoulders.</p>
                    <p>Keep your body in a straight line from head to heels.</p>
                    <p>Engage your core, glutes, and quads.</p>
                    <p>Don't let your hips sag or pike up.</p>
                    <p>Hold the position for the designated time.</p>
                  </div>
                )}
                
                {activeExercise.name.toLowerCase().includes('jumping') && (
                  <div className="space-y-3">
                    <p>Stand with feet together and arms at your sides.</p>
                    <p>Jump up, spreading your feet wider than shoulder-width and bringing arms overhead.</p>
                    <p>Jump again, bringing feet back together and arms down to your sides.</p>
                    <p>Keep a consistent rhythm and stay light on your feet.</p>
                    <p>Land softly by bending your knees slightly.</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">Select an exercise to view instructions.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Workout;