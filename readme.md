# 🚀 LeetCode Tracker

A comprehensive dashboard for tracking and analyzing LeetCode progress of students in a batch. Monitor performance, identify weak areas, and visualize progress with beautiful charts.

## 🌟 Features

### 📊 Dashboard
- **Student Search**: Quick lookup by roll number
- **Performance Metrics**: Easy, Medium, Hard problem counts
- **Difficulty Distribution**: Interactive doughnut chart
- **Weak Areas**: Auto-identified topics needing improvement

### 👥 Student Management
- **Add Students**: Manual addition with roll number, name, and LeetCode usernames
- **Batch Upload**: Excel/CSV upload support (requires pandas)
- **Student List**: View all students with their stats

### 🏆 Leaderboard
- **Ranking**: Auto-ranked by total problems solved
- **Sort Options**: Sort by Easy, Medium, Hard, or Total
- **Quick View**: Click any student to see detailed stats

### 📈 Batch Analytics
- **Batch Statistics**: Total students, problems solved, averages
- **Performance Distribution**: Bar chart breakdown
- **Difficulty Breakdown**: Doughnut chart
- **Top Performers**: Highlight top 3 students

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **Python/Flask** | Backend API and server |
| **SQLite** | Database for storing student data |
| **Chart.js** | Interactive data visualization |
| **HTML/CSS/JS** | Frontend interface |
| **LeetCode GraphQL API** | Fetch user problem stats |

## 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (for cloning)

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Rajan2217/leetcode-tracker.git
cd leetcode-tracker