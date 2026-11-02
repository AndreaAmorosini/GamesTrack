import React, { useState, useEffect } from 'react';
import PageTitle from '../components/Typography/PageTitle';
import {
    Card, CardBody, Button, Badge, Input, Label, Select, HelperText,
} from '@windmill/react-ui';
import { getNtfySettings, updateNtfySettings, testNtfySettings } from '../services/api';
import { useToast } from '../context/ToastContext';

const NTFY_INSTRUCTIONS = [
    'Installa l\'app ntfy dal Play Store / App Store, oppure apri ntfy.sh nel browser.',
    'Scegli un nome di topic non indovinabile: chiunque conosca il nome della topic può leggere le notifiche. Esempio: "gametrack-pippo-8341ab".',
    'Nell\'app ntfy, iscriviti alla topic con lo stesso nome.',
    'Inserisci qui il nome della topic e salva. Il server di default è ntfy.sh; se hai un server ntfy self-hosted, inserisci il suo indirizzo.',
    'Opzionale: se la topic è protetta da autenticazione, inserisci un token di accesso.',
    'Premi "Invia notifica di prova" per verificare: dovresti riceverla sull\'app.',
];

const Settings = () => {
    const { notify } = useToast();
    const [config, setConfig] = useState({
        enabled: false,
        server_url: 'https://ntfy.sh',
        topic: '',
        token: '',
        notify_on_sync: true,
        notify_on_price: true,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const settings = await getNtfySettings();
                setConfig(settings);
            } catch (err) {
                notify('Errore nel caricamento delle impostazioni', 'error');
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const save = async () => {
        try {
            setSaving(true);
            await updateNtfySettings(config);
            notify('Impostazioni notifiche salvate', 'success');
        } catch (err) {
            notify(err.message || 'Errore nel salvataggio', 'error');
        } finally {
            setSaving(false);
        }
    };

    const sendTest = async () => {
        try {
            setTesting(true);
            const res = await testNtfySettings();
            notify(res.message || 'Notifica inviata', 'success');
        } catch (err) {
            notify(err.detail || err.message || 'Invio fallito', 'error');
        } finally {
            setTesting(false);
        }
    };

    return (
        <>
            <PageTitle>Impostazioni</PageTitle>

            <Card className="mb-8">
                <CardBody>
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Notifiche push (ntfy)</h3>
                        <Badge type={config.enabled ? 'success' : 'neutral'}>
                            {config.enabled ? 'Attive' : 'Disattive'}
                        </Badge>
                    </div>

                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        Ricevi sul telefono (o desktop) le notifiche di GamesTrack: sync fallite e alert prezzi.
                    </p>

                    <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <p className="text-sm font-semibold text-blue-700 dark:text-blue-300 mb-2">Setup in 5 passi</p>
                        <ol className="list-decimal list-inside text-sm text-blue-700 dark:text-blue-300 space-y-1">
                            {NTFY_INSTRUCTIONS.map((step, i) => (
                                <li key={i}>{step}</li>
                            ))}
                        </ol>
                    </div>

                    {loading ? (
                        <p className="text-sm text-gray-500">Caricamento impostazioni...</p>
                    ) : (
                        <>
                            <Label>
                                <span>Notifiche attive</span>
                                <Select
                                    className="mt-1"
                                    value={config.enabled ? 'on' : 'off'}
                                    onChange={(e) => setConfig({ ...config, enabled: e.target.value === 'on' })}
                                >
                                    <option value="on">Attive</option>
                                    <option value="off">Disattive</option>
                                </Select>
                            </Label>

                            <Label className="mt-4">
                                <span>Nome della topic</span>
                                <Input
                                    className="mt-1"
                                    placeholder="gametrack-pippo-8341ab"
                                    value={config.topic}
                                    onChange={(e) => setConfig({ ...config, topic: e.target.value })}
                                />
                            </Label>

                            <Label className="mt-4">
                                <span>Server ntfy</span>
                                <Input
                                    className="mt-1"
                                    placeholder="https://ntfy.sh"
                                    value={config.server_url}
                                    onChange={(e) => setConfig({ ...config, server_url: e.target.value })}
                                />
                                <HelperText>Default: ntfy.sh pubblico. Inserisci l'indirizzo del tuo server se self-hosted.</HelperText>
                            </Label>

                            <Label className="mt-4">
                                <span>Token di accesso (opzionale)</span>
                                <Input
                                    className="mt-1"
                                    type="password"
                                    placeholder="Solo per topic protette da autenticazione"
                                    value={config.token}
                                    onChange={(e) => setConfig({ ...config, token: e.target.value })}
                                />
                            </Label>

                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                                <Label>
                                    <span>Notifica quando una sync fallisce</span>
                                    <Select
                                        className="mt-1"
                                        value={config.notify_on_sync ? 'on' : 'off'}
                                        onChange={(e) => setConfig({ ...config, notify_on_sync: e.target.value === 'on' })}
                                    >
                                        <option value="on">Sì</option>
                                        <option value="off">No</option>
                                    </Select>
                                </Label>
                                <Label>
                                    <span>Notifica sugli alert prezzi</span>
                                    <Select
                                        className="mt-1"
                                        value={config.notify_on_price ? 'on' : 'off'}
                                        onChange={(e) => setConfig({ ...config, notify_on_price: e.target.value === 'on' })}
                                    >
                                        <option value="on">Sì</option>
                                        <option value="off">No</option>
                                    </Select>
                                </Label>
                            </div>

                            <div className="mt-6 flex flex-wrap gap-3">
                                <Button onClick={save} disabled={saving}>
                                    {saving ? 'Salvataggio...' : 'Salva impostazioni'}
                                </Button>
                                <Button layout="outline" onClick={sendTest} disabled={testing || !config.topic}>
                                    {testing ? 'Invio...' : 'Invia notifica di prova'}
                                </Button>
                            </div>
                        </>
                    )}
                </CardBody>
            </Card>
        </>
    );
};

export default Settings;
