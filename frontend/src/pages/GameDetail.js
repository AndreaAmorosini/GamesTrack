import React, { useState, useEffect } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import { Card, CardBody, Button, Badge } from '@windmill/react-ui';
import { getGameDetail } from '../services/api';

const TROPHY_STYLES = {
  bronze: { color: '#cd7f32', label: 'Bronzo' },
  silver: { color: '#a8b0b8', label: 'Argento' },
  gold: { color: '#e3a008', label: 'Oro' },
  platinum: { color: '#5ac8fa', label: 'Platino' },
};

const igdbImage = (url, size) => {
  if (!url) return null;
  let u = url.startsWith('http') ? url : `https:${url}`;
  if (size) u = u.replace('t_thumb', size).replace('t_cover_big', size).replace('t_screenshot_big', size).replace('t_original', size);
  return u;
};

const formatDate = (d) => {
  if (!d) return '';
  try {
    return new Date(d).toLocaleDateString('it-IT');
  } catch {
    return d;
  }
};

const PLATFORM_LABELS = {
  steam: 'Steam',
  psn: 'PlayStation Network',
  retroachievements: 'RetroAchievements',
  gog: 'GOG',
};

const SOURCE_LABELS = {
  digital: 'Copia digitale',
  psplus: 'PS Plus',
  unknown: '',
};

const GameDetail = () => {
  const { gameId } = useParams();
  const history = useHistory();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeImage, setActiveImage] = useState(null);

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await getGameDetail(gameId);
        setDetail(data);
        setActiveImage(data.screenshots && data.screenshots.length > 0 ? data.screenshots[0] : null);
      } catch (err) {
        setError(err.message || 'Errore nel caricamento del gioco');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [gameId]);

  if (loading) {
    return (
      <Card>
        <CardBody>
          <p className="text-gray-600 dark:text-gray-300">Caricamento...</p>
        </CardBody>
      </Card>
    );
  }

  if (error || !detail) {
    return (
      <Card>
        <CardBody>
          <p className="text-red-600 dark:text-red-400">{error || 'Gioco non trovato'}</p>
          <Button className="mt-4" onClick={() => history.goBack()}>
            Torna indietro
          </Button>
        </CardBody>
      </Card>
    );
  }

  const coverUrl = igdbImage(detail.cover_image, 't_cover_big') || '/default_cover.png';
  const backdropUrl =
    (detail.artworks && detail.artworks.length > 0 && igdbImage(detail.artworks[0], 't_1080p')) ||
    activeImage ||
    null;
  const heroUrl = backdropUrl || igdbImage(detail.cover_image, 't_720p');
  const screenshots = (detail.screenshots || []).slice(0, 6);

  const trophies = detail.trophies || null;
  const earnedTrophies = trophies ? trophies.filter((t) => t.earned).length : 0;
  const trophyCount = { bronze: 0, silver: 0, gold: 0, platinum: 0 };
  if (trophies) {
    trophies.forEach((t) => {
      if (t.type && trophyCount[t.type] !== undefined) trophyCount[t.type] += 1;
    });
  }
  const earnedCount = { bronze: 0, silver: 0, gold: 0, platinum: 0 };
  if (trophies) {
    trophies.forEach((t) => {
      if (t.earned && t.type && earnedCount[t.type] !== undefined) earnedCount[t.type] += 1;
    });
  }

  const achievements = detail.achievements || null;
  const earnedAchievements = achievements ? achievements.filter((a) => a.earned).length : 0;

  const steamAchievements = detail.steam_achievements || null;
  const earnedSteamAchievements = steamAchievements
    ? steamAchievements.filter((a) => a.achieved).length
    : 0;
  const platformFamilies = detail.platform_families || {};

  const UNAVAILABLE_MESSAGES = {
    psn: {
      not_linked: 'Collega PlayStation Network dalla pagina Servizi per vedere i trofei di questo gioco.',
      no_trophy_data: 'Nessun trofeo PSN sincronizzato per questo gioco: esegui una sincronizzazione PSN.',
      failed: 'Impossibile recuperare i trofei da PSN al momento: riprova più tardi.',
    },
    steam: {
      not_linked: 'Collega Steam (Steam ID + Web API Key) dalla pagina Servizi per vedere gli achievement.',
      no_achievements: 'Questo gioco non ha achievement su Steam.',
      failed: 'Impossibile recuperare gli achievement da Steam al momento.',
    },
    ra: {
      not_linked: 'Collega RetroAchievements dalla pagina Servizi per vedere gli achievement retrò.',
      no_achievements: 'Questo gioco non ha achievement su RetroAchievements.',
      failed: 'Impossibile recuperare gli achievement da RetroAchievements al momento.',
    },
  };

  return (
    <>
      {/* Hero: backdrop + copertina + titolo */}
      <div className="relative mb-6 -mx-4 sm:-mx-6 overflow-hidden">
        {heroUrl && (
          <div
            className="absolute inset-0 bg-cover bg-center opacity-30"
            style={{ backgroundImage: `url(${heroUrl})` }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-gray-50 dark:from-gray-900 to-transparent" />
        <div className="relative flex items-end px-4 sm:px-6 pt-8 pb-4">
          <img
            className="w-24 h-36 sm:w-36 sm:h-56 object-cover rounded-lg shadow-lg mr-4 sm:mr-6"
            src={coverUrl}
            alt={detail.name}
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = '/default_cover.png';
            }}
          />
          <div className="flex-1 min-w-0 pb-1">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white break-words">
              {detail.name}
            </h2>
            {detail.original_name && detail.original_name !== detail.name && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{detail.original_name}</p>
            )}
            <div className="flex flex-wrap items-center gap-2 mt-3">
              {detail.release_year && (
                <Badge type="neutral">{detail.release_year}</Badge>
              )}
              {detail.total_rating != null && (
                <Badge type="success">★ {Number(detail.total_rating).toFixed(1)} / 100</Badge>
              )}
              {(detail.genres || []).slice(0, 3).map((g) => (
                <Badge key={g} type="neutral">{g}</Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Dati utente: voci libreria */}
      {detail.library_entries && detail.library_entries.length > 0 && (
        <div className="grid gap-4 mb-6 md:grid-cols-2">
          {detail.library_entries.map((entry, i) => (
            <Card key={i}>
              <CardBody className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900 dark:text-white">
                    {PLATFORM_LABELS[entry.platform] || entry.platform}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {entry.play_hours
                      ? `${entry.play_hours}h di gioco · ${entry.num_trophies || 0} trofei`
                      : entry.source === 'wishlist'
                      ? 'Nella wishlist'
                      : 'Nella libreria'}
                  </p>
                </div>
                {SOURCE_LABELS[entry.source] && (
                  <Badge type={entry.source === 'psplus' ? 'warning' : 'success'}>
                    {SOURCE_LABELS[entry.source]}
                  </Badge>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      <div className="grid gap-6 mb-6 lg:grid-cols-3">
        {/* Descrizione */}
        <Card className="lg:col-span-2">
          <CardBody>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">Descrizione</h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line leading-relaxed">
              {detail.description || 'Descrizione non disponibile.'}
            </p>
          </CardBody>
        </Card>

        {/* Metadati */}
        <Card>
          <CardBody>
            <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Dettagli</h3>
            <dl className="space-y-2 text-sm">
              {detail.release_date && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Uscita</dt>
                  <dd className="text-gray-900 dark:text-white text-right">{formatDate(detail.release_date)}</dd>
                </div>
              )}
              {(detail.developers || []).length > 0 && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Sviluppo</dt>
                  <dd className="text-gray-900 dark:text-white text-right">{detail.developers.join(', ')}</dd>
                </div>
              )}
              {(detail.publishers || []).length > 0 && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Pubblicazione</dt>
                  <dd className="text-gray-900 dark:text-white text-right">{detail.publishers.join(', ')}</dd>
                </div>
              )}
              {(detail.platforms || []).length > 0 && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Piattaforme</dt>
                  <dd className="text-gray-900 dark:text-white text-right">
                    {(detail.platforms || []).map((p) => p.abbreviation || p.name).join(', ')}
                  </dd>
                </div>
              )}
              {(detail.genres || []).length > 0 && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Generi</dt>
                  <dd className="text-gray-900 dark:text-white text-right">{detail.genres.join(', ')}</dd>
                </div>
              )}
              {(detail.game_modes || []).length > 0 && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Modalità</dt>
                  <dd className="text-gray-900 dark:text-white text-right">{detail.game_modes.join(', ')}</dd>
                </div>
              )}
              {detail.total_rating != null && (
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-500 dark:text-gray-400">Valutazione</dt>
                  <dd className="text-gray-900 dark:text-white text-right">
                    {Number(detail.total_rating).toFixed(1)} ({detail.total_rating_count || 0} voti)
                  </dd>
                </div>
              )}
            </dl>
          </CardBody>
        </Card>
      </div>

      {/* Galleria screenshot */}
      {screenshots.length > 0 && (
        <Card className="mb-6">
          <CardBody>
            <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Immagini</h3>
            {activeImage && (
              <img
                className="w-full rounded-lg mb-3"
                src={igdbImage(activeImage, 't_screenshot_big') || activeImage}
                alt={detail.name}
                loading="lazy"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
            <div className="flex gap-2 overflow-x-auto pb-1">
              {screenshots.map((s, i) => (
                <img
                  key={i}
                  className={`h-16 rounded cursor-pointer flex-shrink-0 ${
                    activeImage === s ? 'ring-2 ring-purple-600' : 'opacity-80'
                  }`}
                  src={igdbImage(s, 't_screenshot_thumb') || s}
                  alt={`${detail.name} ${i + 1}`}
                  loading="lazy"
                  onClick={() => setActiveImage(s)}
                  onError={(e) => {
                    e.target.style.visibility = 'hidden';
                  }}
                />
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Trofei PSN: sezione mostrata solo se il gioco esce su PlayStation */}
      {(platformFamilies.playstation || trophies) && (
      <Card className="mb-6">
        <CardBody>
          <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Trofei PlayStation
          </h3>
          {!trophies && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {UNAVAILABLE_MESSAGES.psn[detail.psn_status] ||
                'Lista trofei non disponibile per questo gioco.'}
            </p>
          )}
          {trophies && (
            <>
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {earnedTrophies} / {trophies.length} ottenuti
                </p>
                {Object.entries(trophyCount).map(
                  ([type, count]) =>
                    count > 0 && (
                      <span key={type} className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-300">
                        <span
                          className="w-3 h-3 rounded-full inline-block"
                          style={{ backgroundColor: TROPHY_STYLES[type].color }}
                        />
                        {earnedCount[type]}/{count} {TROPHY_STYLES[type].label}
                      </span>
                    )
                )}
                {detail.trophy_synced_at && (
                  <span className="text-xs text-gray-400">
                    (lista sincronizzata il {formatDate(detail.trophy_synced_at)})
                  </span>
                )}
              </div>
              <ul className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {trophies.map((t, i) => (
                  <li
                    key={t.trophy_id || i}
                    className={`flex items-start gap-3 p-2 rounded-lg text-sm ${
                      t.earned ? 'bg-white dark:bg-gray-800' : 'opacity-60'
                    }`}
                  >
                    <span
                      className="w-4 h-4 rounded-full flex-shrink-0 mt-1"
                      style={{ backgroundColor: TROPHY_STYLES[t.type]?.color || '#888' }}
                    />
                    {t.icon_url && (
                      <img
                        className="w-10 h-10 rounded object-cover flex-shrink-0"
                        src={t.icon_url.startsWith('http') ? t.icon_url : `https:${t.icon_url}`}
                        alt=""
                        loading="lazy"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white">{t.name}</p>
                      {t.detail && (
                        <p className="text-gray-500 dark:text-gray-400">{t.detail}</p>
                      )}
                      {t.earned && t.earned_date && (
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                          Ottenuto il {formatDate(t.earned_date)}
                          {t.rarity ? ` · ${t.rarity}` : ''}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardBody>
      </Card>
      )}

      {/* Achievement Steam: sezione mostrata solo se il gioco è su Steam */}
      {(platformFamilies.steam || steamAchievements) && (
      <Card className="mb-6">
        <CardBody>
          <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Achievement Steam
          </h3>
          {!steamAchievements && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {UNAVAILABLE_MESSAGES.steam[detail.steam_status] ||
                'Achievement Steam non disponibili per questo gioco.'}
            </p>
          )}
          {steamAchievements && (
            <>
              <p className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                {earnedSteamAchievements} / {steamAchievements.length} ottenuti
              </p>
              <ul className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {steamAchievements.map((a, i) => (
                  <li
                    key={i}
                    className={`flex items-start gap-3 p-2 rounded-lg text-sm ${
                      a.achieved ? 'bg-white dark:bg-gray-800' : 'opacity-60'
                    }`}
                  >
                    {a.icon && (
                      <img
                        className="w-10 h-10 rounded object-cover flex-shrink-0"
                        src={a.achieved ? a.icon : a.icon_gray || a.icon}
                        alt=""
                        loading="lazy"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white">{a.name}</p>
                      {a.description && (
                        <p className="text-gray-500 dark:text-gray-400">{a.description}</p>
                      )}
                      {a.achieved && a.unlock_time && (
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                          Ottenuto il {formatDate(a.unlock_time)}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </CardBody>
      </Card>
      )}

      {/* Achievement RetroAchievements: sezione mostrata solo se il gioco ha achievements RA */}
      {(platformFamilies.retro || achievements) && (
      <Card className="mb-6">
        <CardBody>
          <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
            Achievement RetroAchievements
          </h3>
          {!achievements && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {UNAVAILABLE_MESSAGES.ra[detail.ra_status] ||
                'Achievement RetroAchievements non disponibili per questo gioco.'}
            </p>
          )}
          {achievements && (
            <>
              <p className="text-sm font-medium text-gray-900 dark:text-white mb-4">
                {earnedAchievements} / {achievements.length} ottenuti
              </p>
              <ul className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {achievements.map((a, i) => (
                <li
                  key={a.ra_id || i}
                  className={`flex items-start gap-3 p-2 rounded-lg text-sm ${
                    a.earned ? 'bg-white dark:bg-gray-800' : 'opacity-60'
                  }`}
                >
                  {a.badge_url && (
                    <img
                      className={`w-10 h-10 rounded object-cover flex-shrink-0 ${a.earned ? '' : 'grayscale'}`}
                      src={a.badge_url}
                      alt=""
                      loading="lazy"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {a.name} <span className="text-gray-400">({a.points} pt)</span>
                    </p>
                    <p className="text-gray-500 dark:text-gray-400">{a.description}</p>
                    {a.earned && a.earned_date && (
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                        Ottenuto il {formatDate(a.earned_date)}
                        {a.earned_hardcore && ' · Hardcore'}
                      </p>
                    )}
                  </div>
                </li>
              ))}
              </ul>
            </>
          )}
        </CardBody>
      </Card>
      )}

      <div className="mb-8">
        <Button layout="outline" onClick={() => history.goBack()}>
          Torna indietro
        </Button>
      </div>
    </>
  );
};

export default GameDetail;
