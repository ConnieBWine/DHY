import React, { useState, useEffect, useContext } from 'react';
import WorkoutStats from '../components/WorkoutStats';
import { WorkoutContext } from '../context/WorkoutContext';
import apiService from '../services/apiService';

const Analysis = () => {
  const { sessionStats, updateSessionStats } = useContext(WorkoutContext);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('session'); // 'session', 'week', 'month'
  
  // Fetch session stats on component mount
  useEffect(() => {
    const fetchStats = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Only fetch from API if we don't have stats in context
        if (!sessionStats || Object.keys(sessionStats).length === 0) {
          const response = await apiService.getSessionStats();
          updateSessionStats(response);
        }
      } catch (err) {
        console.error('Error fetching session stats:', err);
        setError(apiService.handleApiError(err));
      } finally {
        setLoading(false);
      }
    };
    
    fetchStats();
  }, [sessionStats, updateSessionStats]);
  
  // Generate mock data for week/month views since we don't have actual historical data
  const generateMockHistoricalData = () => {
    // Start with current session data
    const baseStats = sessionStats || {
      common_issues: [],
      exercise_stats: {}
    };
    
    // Add more variety to the data based on time range
    if (timeRange === 'week') {
      // Add some additional issues for weekly view
      const weeklyIssues = [
        ...baseStats.common_issues,
        ["Inconsistent exercise pace", Math.floor(Math.random() * 10) + 5],
        ["Exercises completed outside target heart rate zone", Math.floor(Math.random() * 8) + 3]
      ];
      
      // Sort by frequency
      weeklyIssues.sort((a, b) => b[1] - a[1]);
      
      return {
        ...baseStats,
        common_issues: weeklyIssues,
        total_workouts: Math.floor(Math.random() * 3) + 4, // 4-7 workouts per week
        total_exercises: Math.floor(Math.random() * 20) + 15,
        workout_minutes: Math.floor(Math.random() * 150) + 180 // 180-330 minutes
      };
    } else if (timeRange === 'month') {
      // Add more issues for monthly view
      const monthlyIssues = [
        ...baseStats.common_issues,
        ["Inconsistent exercise pace", Math.floor(Math.random() * 15) + 10],
        ["Exercises completed outside target heart rate zone", Math.floor(Math.random() * 12) + 8],
        ["Insufficient recovery between workouts", Math.floor(Math.random() * 6) + 4],
        ["Unbalanced muscle group focus", Math.floor(Math.random() * 5) + 3]
      ];
      
      // Sort by frequency
      monthlyIssues.sort((a, b) => b[1] - a[1]);
      
      return {
        ...baseStats,
        common_issues: monthlyIssues,
        total_workouts: Math.floor(Math.random() * 8) + 15, // 15-23 workouts per month
        total_exercises: Math.floor(Math.random() * 40) + 60,
        workout_minutes: Math.floor(Math.random() * 300) + 700 // 700-1000 minutes
      };
    }
    
    // Default to session data
    return baseStats;
  };
  
  // Get appropriate stats based on selected time range
  const getDisplayStats = () => {
    if (timeRange === 'session') {
      return sessionStats;
    } else {
      return generateMockHistoricalData();
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Workout Analysis</h1>
        
        {/* Time range selector */}
        <div className="flex p-1 bg-gray-100 rounded-md">
          <button 
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              timeRange === 'session' 
                ? 'bg-white text-primary-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
            onClick={() => setTimeRange('session')}
          >
            Current Session
          </button>
          <button 
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              timeRange === 'week' 
                ? 'bg-white text-primary-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
            onClick={() => setTimeRange('week')}
          >
            This Week
          </button>
          <button 
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              timeRange === 'month' 
                ? 'bg-white text-primary-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-900'
            }`}
            onClick={() => setTimeRange('month')}
          >
            This Month
          </button>
        </div>
      </div>
      
      {/* Loading state */}
      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
        </div>
      )}
      
      {/* Error state */}
      {error && (
        <div className="bg-error-100 border border-error-300 text-error-700 px-4 py-3 rounded">
          <p>{error}</p>
        </div>
      )}
      
      {/* Stats display */}
      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Overview stats */}
          {(timeRange === 'week' || timeRange === 'month') && (
            <div className="col-span-full grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="card">
                <h3 className="text-gray-500 font-medium">Total Workouts</h3>
                <p className="text-3xl font-bold mt-2">{getDisplayStats().total_workouts || 0}</p>
              </div>
              
              <div className="card">
                <h3 className="text-gray-500 font-medium">Total Exercises</h3>
                <p className="text-3xl font-bold mt-2">{getDisplayStats().total_exercises || 0}</p>
              </div>
              
              <div className="card">
                <h3 className="text-gray-500 font-medium">Workout Minutes</h3>
                <p className="text-3xl font-bold mt-2">{getDisplayStats().workout_minutes || 0}</p>
              </div>
            </div>
          )}
          
          {/* Detailed stats */}
          <div className="md:col-span-3">
            <WorkoutStats sessionStats={getDisplayStats()} />
          </div>
          
          {/* Tips based on common issues */}
          {getDisplayStats()?.common_issues?.length > 0 && (
            <div className="md:col-span-3">
              <div className="card">
                <h2 className="text-xl font-bold mb-4">Personalized Improvement Tips</h2>
                <div className="space-y-4">
                  {getDisplayStats().common_issues.slice(0, 3).map((issue, index) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-lg">
                      <h3 className="font-semibold text-primary-700">{issue[0]}</h3>
                      
                      {/* Dynamic tips based on the issue */}
                      {issue[0].toLowerCase().includes('form') && (
                        <p className="mt-2 text-gray-700">
                          Focus on slower, more controlled movements to maintain proper form. Consider reducing weight or intensity to master the technique first.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('elbow') && (
                        <p className="mt-2 text-gray-700">
                          Keep your elbows close to your body during bicep curls. Try performing the exercise in front of a mirror to monitor elbow position.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('bend') && (
                        <p className="mt-2 text-gray-700">
                          Practice proper hip hinge movement patterns by focusing on pushing your hips back rather than bending forward from the waist.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('deep') && (
                        <p className="mt-2 text-gray-700">
                          Work on improving your squat depth gradually. Use a box or bench as a depth gauge to ensure consistency.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('hip') && (
                        <p className="mt-2 text-gray-700">
                          Strengthen your core with targeted exercises like planks and dead bugs to help maintain proper hip alignment during workouts.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('knee') && (
                        <p className="mt-2 text-gray-700">
                          Focus on keeping your knees in line with your toes during squats and lunges. Consider adding lateral band walks to strengthen stabilizing muscles.
                        </p>
                      )}
                      
                      {issue[0].toLowerCase().includes('pace') && (
                        <p className="mt-2 text-gray-700">
                          Try using a metronome or following a rhythm to maintain consistent exercise tempo. This helps improve muscle engagement and exercise effectiveness.
                        </p>
                      )}
                      
                      {/* Generic tips for any issues not specifically addressed */}
                      {!issue[0].toLowerCase().match(/(form|elbow|bend|deep|hip|knee|pace)/) && (
                        <p className="mt-2 text-gray-700">
                          Consider recording your workouts occasionally to review your technique. Small adjustments to your form can lead to significant improvements.
                        </p>
                      )}
                      
                      <div className="mt-3 text-xs text-gray-500">
                        Occurred {issue[1]} times in this {timeRange}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Analysis;