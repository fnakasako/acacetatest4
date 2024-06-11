// src/components/HomePage.js
import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const containerStyle = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    textAlign: 'center',
  };

  const logoStyle = {
    fontSize: '3rem',
    marginBottom: '20px',
  };

  const buttonStyle = {
    padding: '10px 20px',
    fontSize: '1rem',
    cursor: 'pointer',
  };

  return (
    <div style={containerStyle}>
      <h1 style={logoStyle}>Acaceta</h1>
      <Link to="/login">
        <button style={buttonStyle}>Login</button>
      </Link>
    </div>
  );
};

export default HomePage;

