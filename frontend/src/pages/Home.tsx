import React from 'react';

const Home: React.FC = () => {
  return (
    <div style={{
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto'
    }}>
      <h1>Benvenuto su GamesTrack</h1>
      <p>La tua piattaforma per tenere traccia dei tuoi giochi preferiti</p>
      
      <div style={{
        marginTop: '2rem',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '2rem'
      }}>
        <div className="feature-card" style={{
          padding: '1.5rem',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h3>Traccia i tuoi Giochi</h3>
          <p>Mantieni un registro di tutti i giochi che possiedi e quelli che desideri.</p>
        </div>

        <div className="feature-card" style={{
          padding: '1.5rem',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h3>Statistiche</h3>
          <p>Visualizza statistiche dettagliate sulla tua collezione di giochi.</p>
        </div>

        <div className="feature-card" style={{
          padding: '1.5rem',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h3>Multi-piattaforma</h3>
          <p>Supporto per Steam, PSN e altre piattaforme di gaming.</p>
        </div>
      </div>
    </div>
  );
};

export default Home; 