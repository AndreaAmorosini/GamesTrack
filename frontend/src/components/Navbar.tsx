import React from 'react';

const Navbar: React.FC = () => {
  return (
    <nav style={{
      backgroundColor: '#333',
      padding: '1rem',
      color: 'white',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }}>
      <div className="logo">
        <h1>GamesTrack</h1>
      </div>
      <div className="nav-links" style={{
        display: 'flex',
        gap: '1rem'
      }}>
        <a href="/" style={{ color: 'white', textDecoration: 'none' }}>Home</a>
        <a href="/games" style={{ color: 'white', textDecoration: 'none' }}>Games</a>
        <a href="/profile" style={{ color: 'white', textDecoration: 'none' }}>Profile</a>
      </div>
    </nav>
  );
};

export default Navbar; 