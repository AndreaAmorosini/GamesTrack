import React, { useState, useEffect } from 'react';
import PageTitle from '../components/Typography/PageTitle';
import SectionTitle from '../components/Typography/SectionTitle';
import {
    Card, CardBody, Button, Badge, Input, Label,
    Select, HelperText,
} from '@windmill/react-ui';
import {
    getUserProfile, updateUserProfile,
    getPriceTrackSettings, updatePriceTrackSettings, runPriceTrackNow,
    getPlatformSyncSettings, updatePlatformSyncSettings,
} from '../services/api';
import { useToast } from '../context/ToastContext';

// Istruzioni per ottenere le credenziali di ciascuna piattaforma
const PLATFORM_INSTRUCTIONS = {
    steam: {
        name: 'Steam',
        badgeType: 'success',
        dataNeeded: [
            { field: 'steam', label: 'Steam ID', help: 'Il tuo identificativo Steam (17 cifre, es. 76561198012345678). Lo trovi nel tuo profilo: apri i Dettagli account da steamcommunity.com o dal client Steam, oppure usa steamid.io.' },
            { field: 'steam_api_key', label: 'Steam Web API Key', help: 'Genera una chiave gratuita su steamcommunity.com/dev/apikey: serve un dominio qualsiasi (anche localhost) e la chiave appare subito.' },
        ],
        note: 'Il sync recupera la libreria completa, il tempo di gioco e gli achievement.',
    },
    psn: {
        name: 'PlayStation Network',
        badgeType: 'warning',
        dataNeeded: [
            { field: 'psn', label: 'PSN Online ID', help: 'Il tuo nome utente PlayStation visibile sul profilo.' },
            { field: 'psn_api_key', label: 'NPSSO', help: '1. Accedi a my.playstation.com. 2. In un\'altra scheda apri ca.account.sony.com/api/v1/ssocookie. 3. Se sei loggato vedrai {"npsso":"<codice a 64 caratteri>"}: copia il valore.' },
        ],
        note: 'Il sync recupera giochi, trofei e statistiche di gioco.',
    },
    retroachievements: {
        name: 'RetroAchievements',
        badgeType: 'danger',
        dataNeeded: [
            { field: 'ra', label: 'Username RetroAchievements', help: 'Il tuo nome utente su retroachievements.org.' },
            { field: 'ra_api_key', label: 'Web API Key', help: 'Accedi a retroachievements.org, apri le impostazioni account (retroachievements.org/settings) e copia la Web API Key.' },
        ],
        note: 'Il sync recupera i giochi masterizzati/completati e quelli giocati di recente con i conteggi achievement.',
    },
    gog: {
        name: 'GOG',
        badgeType: 'neutral',
        dataNeeded: [
            { field: 'gog', label: 'GOG Email/Username', help: 'Email o username del tuo account GOG.' },
            { field: 'gog_password', label: 'GOG Password', help: 'Password dell\'account. Attenzione: gli account con autenticazione a due fattori non sono supportati.' },
        ],
        note: 'Il sync recupera solo la lista dei titoli posseduti (GOG non espone statistiche di gioco).',
    },
};

const Services = () => {
    const { notify } = useToast();
    // --- Configurazione piattaforme ---
    const [formData, setFormData] = useState({
        steam: '', steam_api_key: '',
        psn: '', psn_api_key: '',
        ra: '', ra_api_key: '',
        gog: '', gog_password: '',
    });
    const [profileLoading, setProfileLoading] = useState(true);
    const [savingPlatform, setSavingPlatform] = useState(null);
    // Tab mobile: su smartphone si mostra una piattaforma alla volta
    const [mobileTab, setMobileTab] = useState('steam');

    // --- Impostazioni tracking prezzi ---
    const [priceSettings, setPriceSettings] = useState({
        enabled: true, interval_minutes: 1440, last_run: null, trovaprezzi_stores: [],
    });
    const [priceLoading, setPriceLoading] = useState(true);
    const [priceSaving, setPriceSaving] = useState(false);
    const [priceRunning, setPriceRunning] = useState(false);
    const [newStore, setNewStore] = useState('');

    const loadProfile = async () => {
        try {
            const userData = await getUserProfile();
            setFormData(prev => ({
                ...prev,
                steam: userData.steam || '',
                steam_api_key: userData.steam_api_key || '',
                psn: userData.psn || '',
                psn_api_key: userData.psn_api_key || '',
                ra: userData.ra || '',
                ra_api_key: userData.ra_api_key || '',
                gog: userData.gog || '',
                gog_password: userData.gog_password || '',
            }));
        } catch (err) {
            console.error('Error loading profile:', err);
        } finally {
            setProfileLoading(false);
        }
    };

    const loadPriceSettings = async () => {
        try {
            const settings = await getPriceTrackSettings();
            setPriceSettings({
                enabled: settings.enabled,
                interval_minutes: settings.interval_minutes,
                last_run: settings.last_run,
                trovaprezzi_stores: settings.trovaprezzi_stores || [],
            });
        } catch (err) {
            console.error('Error loading price settings:', err);
        } finally {
            setPriceLoading(false);
        }
    };

    useEffect(() => {
        loadProfile();
        loadPriceSettings();
    }, []);

    const CREDENTIAL_FIELDS = {
        steam: { id: 'steam', key: 'steam_api_key' },
        psn: { id: 'psn', key: 'psn_api_key' },
        retroachievements: { id: 'ra', key: 'ra_api_key' },
        gog: { id: 'gog', key: 'gog_password' },
    };

    const savePlatform = async (platform) => {
        try {
            setSavingPlatform(platform);
            const { id, key } = CREDENTIAL_FIELDS[platform];
            await updateUserProfile({ [id]: formData[id], [key]: formData[key] });
            notify(`Credenziali ${PLATFORM_INSTRUCTIONS[platform].name} salvate`, 'success');
        } catch (err) {
            notify(err.message || 'Errore nel salvataggio delle credenziali', 'error');
        } finally {
            setSavingPlatform(null);
        }
    };

    // --- Sincronizzazione automatica piattaforme ---
    const [syncSettings, setSyncSettings] = useState({ enabled: false, weekday: 0, hour: 8, last_run: null });
    const [syncSettingsSaving, setSyncSettingsSaving] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                setSyncSettings(await getPlatformSyncSettings());
            } catch (err) {
                console.error('Error loading platform sync settings:', err);
            }
        })();
    }, []);

    const saveSyncSettings = async () => {
        try {
            setSyncSettingsSaving(true);
            await updatePlatformSyncSettings(syncSettings);
            notify('Sincronizzazione automatica configurata', 'success');
        } catch (err) {
            notify(err.message || 'Errore nel salvataggio', 'error');
        } finally {
            setSyncSettingsSaving(false);
        }
    };

    const savePriceSettings = async () => {
        try {
            setPriceSaving(true);
            await updatePriceTrackSettings({
                enabled: priceSettings.enabled,
                interval_minutes: parseInt(priceSettings.interval_minutes) || 1440,
                trovaprezzi_stores: (priceSettings.trovaprezzi_stores || []).map(s => s.trim()).filter(Boolean),
            });
            notify('Impostazioni salvate: il worker le applica entro un minuto', 'success');
        } catch (err) {
            notify(err.message || 'Errore nel salvataggio', 'error');
        } finally {
            setPriceSaving(false);
        }
    };

    const runPriceTrack = async () => {
        try {
            setPriceRunning(true);
            await runPriceTrackNow();
            notify('Tracking prezzi avviato: monitora il progresso nella pagina Storico Sincronizzazioni', 'success');
        } catch (err) {
            notify(err.message || "Errore nell'avvio del tracking", 'error');
        } finally {
            setPriceRunning(false);
        }
    };

    // Una piattaforma è "connessa" se l'identificatore utente è configurato
    const isConnected = (platform) => Boolean(formData[CREDENTIAL_FIELDS[platform].id]);

    return (
        <>
            <PageTitle>Servizi</PageTitle>

            {/* --- Sync piattaforme --- */}
            <SectionTitle>Sincronizzazione piattaforme</SectionTitle>

            {/* Tab di selezione (solo mobile: su desktop si vedono tutte le card) */}
            <div className="md:hidden flex flex-wrap gap-2 mb-4">
                {Object.entries(PLATFORM_INSTRUCTIONS).map(([platform, info]) => (
                    <Button
                        key={platform}
                        size="small"
                        layout={mobileTab === platform ? 'primary' : 'outline'}
                        onClick={() => setMobileTab(platform)}
                    >
                        {info.name}
                        {isConnected(platform) && (
                            <span className="ml-1 inline-block w-2 h-2 bg-green-500 rounded-full" aria-hidden="true" />
                        )}
                    </Button>
                ))}
            </div>

            <div className="grid gap-6 mb-8 md:grid-cols-2">
                {Object.entries(PLATFORM_INSTRUCTIONS).map(([platform, info]) => {
                    // Su mobile mostra solo la piattaforma selezionata dal tab;
                    // su desktop tutte le card sono visibili
                    return (
                    <Card key={platform} className={mobileTab !== platform ? 'hidden md:block' : ''}>
                        <CardBody>
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{info.name}</h3>
                                <div className="flex items-center gap-2">
                                    <Badge type={isConnected(platform) ? 'success' : 'neutral'}>
                                        {isConnected(platform) ? 'Connesso' : 'Da configurare'}
                                    </Badge>
                                    <Badge type={info.badgeType}>{info.name}</Badge>
                                </div>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{info.note}</p>

                            {info.dataNeeded.map((d) => (
                                <Label key={d.field} className="mt-3">
                                    <span className="font-medium">{d.label}</span>
                                    <Input
                                        className="mt-1"
                                        name={d.field}
                                        type={d.field.includes('key') || d.field.includes('password') || d.field === 'psn_api_key' ? 'password' : 'text'}
                                        placeholder={d.label}
                                        value={formData[d.field]}
                                        onChange={(e) => setFormData({ ...formData, [d.field]: e.target.value })}
                                    />
                                    <HelperText className="mt-1">{d.help}</HelperText>
                                </Label>
                            ))}

                            <div className="mt-4 flex items-center gap-3">
                                <Button
                                    onClick={() => savePlatform(platform)}
                                    disabled={savingPlatform === platform || profileLoading}
                                >
                                    {savingPlatform === platform ? 'Salvataggio...' : 'Salva credenziali'}
                                </Button>
                            </div>
                        </CardBody>
                    </Card>
                    );
                })}
            </div>

            {/* --- Tracking prezzi --- */}
            <SectionTitle>Tracking prezzi wishlist</SectionTitle>
            <Card className="mb-8">
                <CardBody>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        Il job raccoglie periodicamente i prezzi per gli item in wishlist dagli store digitali
                        (Steam, GOG, PSN se configurato) e, dove configurato dall'item, dai feed RSS Trovaprezzi
                        dei negozi fisici. La frequenza è modificabile qui sotto.
                    </p>

                    {priceLoading ? (
                        <p className="text-sm text-gray-500">Caricamento impostazioni...</p>
                    ) : (
                        <>
                        <div className="grid gap-4 md:grid-cols-3">
                            <Label>
                                <span>Tracking attivo</span>
                                <Select
                                    className="mt-1"
                                    value={priceSettings.enabled ? 'on' : 'off'}
                                    onChange={(e) => setPriceSettings({ ...priceSettings, enabled: e.target.value === 'on' })}
                                >
                                    <option value="on">Attivo</option>
                                    <option value="off">Disattivo</option>
                                </Select>
                            </Label>
                            <Label>
                                <span>Intervallo (minuti)</span>
                                <Input
                                    className="mt-1"
                                    type="number"
                                    min="5"
                                    max="10080"
                                    value={priceSettings.interval_minutes}
                                    onChange={(e) => setPriceSettings({ ...priceSettings, interval_minutes: e.target.value })}
                                />
                                <HelperText>Minimo 5 minuti, massimo 7 giorni (10080)</HelperText>
                            </Label>
                            <Label>
                                <span>Ultima esecuzione</span>
                                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                                    {priceSettings.last_run ? new Date(priceSettings.last_run).toLocaleString('it-IT') : 'Mai eseguito'}
                                </p>
                            </Label>
                        </div>

                        {/* Lista negozi Trovaprezzi (filtro globale) */}
                        <div className="mt-5">
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                Negozi Trovaprezzi di interesse
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-2">
                                Filtro applicato a tutti gli item della wishlist che non hanno una lista propria:
                                solo le offerte di questi negozi vengono registrate. Esempi: Unieuro, GameStop, Mediaworld, Amazon.
                            </p>
                            <div className="flex flex-wrap items-center gap-2 mb-2">
                                {(priceSettings.trovaprezzi_stores || []).map((store) => (
                                    <span
                                        key={store}
                                        className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-purple-100 dark:bg-purple-900 text-sm text-purple-700 dark:text-purple-200"
                                    >
                                        {store}
                                        <button
                                            type="button"
                                            aria-label={`Rimuovi ${store}`}
                                            className="text-purple-500 hover:text-purple-700 dark:text-purple-300 dark:hover:text-purple-100 font-bold"
                                            onClick={() =>
                                                setPriceSettings({
                                                    ...priceSettings,
                                                    trovaprezzi_stores: priceSettings.trovaprezzi_stores.filter(s => s !== store),
                                                })
                                            }
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                                {(!priceSettings.trovaprezzi_stores || priceSettings.trovaprezzi_stores.length === 0) && (
                                    <span className="text-sm text-gray-400 dark:text-gray-500">
                                        Nessun negozio: verranno accettate tutte le offerte Trovaprezzi
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2 max-w-sm">
                                <Input
                                    className="mt-0"
                                    type="text"
                                    placeholder="Aggiungi un negozio..."
                                    value={newStore}
                                    onChange={(e) => setNewStore(e.target.value)}
                                    onKeyPress={(e) => {
                                        if (e.key === 'Enter' && newStore.trim()) {
                                            e.preventDefault()
                                            const store = newStore.trim()
                                            if (!priceSettings.trovaprezzi_stores.includes(store)) {
                                                setPriceSettings({
                                                    ...priceSettings,
                                                    trovaprezzi_stores: [...(priceSettings.trovaprezzi_stores || []), store],
                                                })
                                            }
                                            setNewStore('')
                                        }
                                    }}
                                />
                                <Button
                                    layout="outline"
                                    onClick={() => {
                                        const store = newStore.trim()
                                        if (store && !priceSettings.trovaprezzi_stores.includes(store)) {
                                            setPriceSettings({
                                                ...priceSettings,
                                                trovaprezzi_stores: [...(priceSettings.trovaprezzi_stores || []), store],
                                            })
                                        }
                                        setNewStore('')
                                    }}
                                >
                                    Aggiungi
                                </Button>
                            </div>
                        </div>
                        </>
                    )}

                    <div className="mt-4 flex items-center gap-3">
                        <Button onClick={savePriceSettings} disabled={priceSaving || priceLoading}>
                            {priceSaving ? 'Salvataggio...' : 'Salva impostazioni'}
                        </Button>
                        <Button layout="outline" onClick={runPriceTrack} disabled={priceRunning}>
                            {priceRunning ? 'Avvio...' : 'Esegui ora'}
                        </Button>
                    </div>
                </CardBody>
            </Card>

            {/* --- Sincronizzazione automatica piattaforme --- */}
            <SectionTitle>Sincronizzazione automatica</SectionTitle>
            <Card className="mb-8">
                <CardBody>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        Sincronizza automaticamente tutte le piattaforme collegate (di tutti gli utenti)
                        al giorno e nell'ora scelti. Configurabile anche da qui in qualsiasi momento.
                    </p>

                    <div className="grid gap-4 md:grid-cols-3">
                        <Label>
                            <span>Sincronizzazione automatica</span>
                            <Select
                                className="mt-1"
                                value={syncSettings.enabled ? 'on' : 'off'}
                                onChange={(e) => setSyncSettings({ ...syncSettings, enabled: e.target.value === 'on' })}
                            >
                                <option value="on">Attiva</option>
                                <option value="off">Disattiva</option>
                            </Select>
                        </Label>
                        <Label>
                            <span>Giorno della settimana</span>
                            <Select
                                className="mt-1"
                                value={syncSettings.weekday}
                                onChange={(e) => setSyncSettings({ ...syncSettings, weekday: parseInt(e.target.value) })}
                            >
                                <option value="0">Lunedì</option>
                                <option value="1">Martedì</option>
                                <option value="2">Mercoledì</option>
                                <option value="3">Giovedì</option>
                                <option value="4">Venerdì</option>
                                <option value="5">Sabato</option>
                                <option value="6">Domenica</option>
                            </Select>
                        </Label>
                        <Label>
                            <span>Ora</span>
                            <Select
                                className="mt-1"
                                value={syncSettings.hour}
                                onChange={(e) => setSyncSettings({ ...syncSettings, hour: parseInt(e.target.value) })}
                            >
                                {Array.from({ length: 24 }).map((_, h) => (
                                    <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
                                ))}
                            </Select>
                        </Label>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-3">
                        <Button onClick={saveSyncSettings} disabled={syncSettingsSaving}>
                            {syncSettingsSaving ? 'Salvataggio...' : 'Salva'}
                        </Button>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                            Ultima esecuzione: {syncSettings.last_run ? new Date(syncSettings.last_run).toLocaleString('it-IT') : 'mai'}
                        </span>
                    </div>
                </CardBody>
            </Card>
        </>
    );
};

export default Services;
