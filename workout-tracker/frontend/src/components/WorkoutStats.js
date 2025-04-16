import React from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  ArcElement, 
  Tooltip, 
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
);

const WorkoutStats = ({ sessionStats, className = '' }) => {
  // Check if stats are available
  const hasStats = sessionStats && 
                   Object.keys(sessionStats).length > 0 && 
                   sessionStats.common_issues && 
                   sessionStats.exercise_stats;
  
  // Format data for pie chart of exercise distribution
  const prepareExerciseDistributionData = () => {
    if (!hasStats) return null;
    
    const exerciseStats = sessionStats.exercise_stats;
    const exerciseNames = Object.keys(exerciseStats);
    
    // Count total feedback items for each exercise
    const exerciseCounts = exerciseNames.map(name => {
      const totalIssues = exerciseStats[name].common_issues.reduce((sum, issue) => sum + issue[1], 0);
      return totalIssues;
    });
    
    return {
      labels: exerciseNames.map(name => name.charAt(0).toUpperCase() + name.slice(1)),
      datasets: [
        {
          data: exerciseCounts,
          backgroundColor: [
            'rgba(255, 99, 132, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(255, 159, 64, 0.6)',
          ],
          borderColor: [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)',
            'rgba(255, 159, 64, 1)',
          ],
          borderWidth: 1,
        },
      ],
    };
  };
  
  // Format data for bar chart of common issues
  const prepareCommonIssuesData = () => {
    if (!hasStats || !sessionStats.common_issues.length) return null;
    
    // Get top 5 issues
    const issues = sessionStats.common_issues.slice(0, 5);
    
    return {
      labels: issues.map(issue => issue[0]),
      datasets: [
        {
          label: 'Occurrences',
          data: issues.map(issue => issue[1]),
          backgroundColor: 'rgba(75, 192, 192, 0.6)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1,
        },
      ],
    };
  };

  // Chart options
  const pieOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom',
      },
      title: {
        display: true,
        text: 'Exercise Distribution',
      },
    },
  };
  
  const barOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: 'Most Common Issues',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0
        }
      }
    }
  };

  // Prepare chart data
  const exerciseDistributionData = prepareExerciseDistributionData();
  const commonIssuesData = prepareCommonIssuesData();

  return (
    <div className={`${className}`}>
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Workout Statistics</h2>
        
        {hasStats ? (
          <div className="space-y-6">
            {/* Exercise distribution chart */}
            {exerciseDistributionData && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Exercise Feedback Distribution</h3>
                <div className="h-64">
                  <Pie data={exerciseDistributionData} options={pieOptions} />
                </div>
              </div>
            )}
            
            {/* Common issues chart */}
            {commonIssuesData && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Most Common Form Issues</h3>
                <div className="h-64">
                  <Bar data={commonIssuesData} options={barOptions} />
                </div>
              </div>
            )}
            
            {/* Exercise-specific feedback */}
            <div>
              <h3 className="text-lg font-semibold mb-2">Exercise-Specific Feedback</h3>
              <div className="space-y-4">
                {Object.entries(sessionStats.exercise_stats).map(([exercise, stats]) => (
                  <div key={exercise} className="p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-primary-700">
                      {exercise.charAt(0).toUpperCase() + exercise.slice(1)}
                    </h4>
                    
                    {stats.common_issues.length > 0 ? (
                      <ul className="mt-2 space-y-1">
                        {stats.common_issues.map((issue, index) => (
                          <li key={index} className="flex justify-between items-center text-sm">
                            <span>{issue[0]}</span>
                            <span className="bg-primary-100 text-primary-800 px-2 py-0.5 rounded-full text-xs">
                              {issue[1]} times
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-500 mt-2">No issues detected</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="text-gray-500 mt-4">No workout data available yet. Complete a workout session to see statistics.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkoutStats;