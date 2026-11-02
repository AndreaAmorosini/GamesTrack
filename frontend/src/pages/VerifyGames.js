import React, { useState, useEffect } from 'react';
import PageTitle from '../components/Typography/PageTitle';
import {
    Card, CardBody, Button, Badge, Pagination,
    Modal, ModalHeader, ModalBody, ModalFooter, Input, Label,
} from '@windmill/react-ui';
import { SearchIcon } from '../icons';
import { getGamesToVerify, resolveVerifyGame, searchIGDBGames } from '../services/api';
import { useToast } from '../context/ToastContext';
import GameNameLink from '../components/GameNameLink';

const VerifyGames = () => {
    const { notify } = useToast();
    const [games, setGames] = useState([]);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalGames, setTotalGames] = useState(0);
    const [loading, setLoading] = useState(true);
    const [resolving, setResolving] = useState(null);

    // Stato per il modal di risoluzione
    const [modalGame, setModalGame] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);

    const fetchGames = async () => {
        try {
            setLoading(true);
            const data = await getGamesToVerify(page);
            setGames(data.games || []);
            setTotalPages(data.total_pages || 1);
            setTotalGames(data.total_count || 0);
        } catch (err) {
            notify(err.message || 'Errore nel caricamento dei giochi da verificare', 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGames();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [page]);

    const openResolveModal = (game) => {
        setModalGame(game);
        setSearchTerm(game.original_name || game.name || '');
        setSearchResults([]);
    };

    const runSearch = async () => {
        if (!searchTerm.trim()) return;
        try {
            setSearching(true);
            const data = await searchIGDBGames(searchTerm);
            setSearchResults(data.games || []);
        } catch (err) {
            notify(err.message || 'Errore nella ricerca IGDB', 'error');
        } finally {
            setSearching(false);
        }
    };

    const resolveGame = async (igdbId) => {
        try {
            setResolving(igdbId);
            const res = await resolveVerifyGame(modalGame._id, igdbId);
            notify(res.message || 'Gioco verificato', 'success');
            setModalGame(null);
            fetchGames();
        } catch (err) {
            notify(err.message || 'Errore nella risoluzione', 'error');
        } finally {
            setResolving(null);
        }
    };

    return (
        <>
            <PageTitle>Giochi da Verificare</PageTitle>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Questi giochi sono entrati in libreria durante una sincronizzazione, ma il matching automatico
                con IGDB è fallito o incerto (il nome del gioco trovato sulla piattaforma non corrispondeva
                con certezza). Cercali su IGDB e conferma la corrispondenza per completarne metadati e copertina.
            </p>

            <Card className="mb-8">
                <CardBody>
                    {loading ? (
                        <p className="text-gray-500">Caricamento...</p>
                    ) : games.length === 0 ? (
                        <div className="text-center py-8">
                            <Badge type="success">Tutto in ordine</Badge>
                            <p className="mt-3 text-gray-600 dark:text-gray-400">
                                Nessun gioco da verificare: tutte le voci della libreria hanno un match IGDB confermato.
                            </p>
                        </div>
                    ) : (
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            {games.map((game) => (
                                <Card key={game._id} className="hover:shadow-lg transition-shadow duration-200">
                                    <CardBody>
                                        <div className="flex items-start justify-between mb-3">
                                            <img
                                                className="w-12 h-12 rounded object-cover"
                                                src={game.cover_image || '/default_cover.png'}
                                                alt={game.name}
                                                onError={(e) => { e.target.onerror = null; e.target.src = '/default_cover.png'; }}
                                            />
                                            <Badge type="danger">Da verificare</Badge>
                                        </div>
                                        <GameNameLink name={game.name} gameId={game.igdb_id} className="block" />
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                            Nome originale: {game.original_name || game.name}
                                            {game.steam_game_id ? ` · Steam ${game.steam_game_id}` : ''}
                                            {game.psn_game_id ? ` · PSN ${game.psn_game_id}` : ''}
                                            {game.ra_game_id ? ` · RA ${game.ra_game_id}` : ''}
                                            {game.gog_game_id ? ` · GOG ${game.gog_game_id}` : ''}
                                        </p>
                                        <Button
                                            size="small"
                                            className="mt-3"
                                            onClick={() => openResolveModal(game)}
                                        >
                                            <SearchIcon className="w-4 h-4 mr-2" aria-hidden="true" />
                                            Cerca su IGDB
                                        </Button>
                                    </CardBody>
                                </Card>
                            ))}
                        </div>
                    )}

                    {totalPages > 1 && (
                        <div className="mt-6 flex justify-center">
                            <Pagination
                                totalResults={totalGames}
                                resultsPerPage={20}
                                onChange={setPage}
                                label="Verify navigation"
                            />
                        </div>
                    )}
                </CardBody>
            </Card>

            {/* Modal risoluzione */}
            <Modal isOpen={!!modalGame} onClose={() => setModalGame(null)}>
                <ModalHeader>
                    Verifica: {modalGame?.name}
                </ModalHeader>
                <ModalBody>
                    <Label>
                        <span>Cerca il gioco su IGDB</span>
                        <div className="flex gap-2 mt-1">
                            <Input
                                placeholder={modalGame?.original_name || modalGame?.name}
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && runSearch()}
                            />
                            <Button onClick={runSearch} disabled={searching}>
                                {searching ? 'Ricerca...' : 'Cerca'}
                            </Button>
                        </div>
                    </Label>

                    <div className="mt-4 space-y-2 max-h-72 overflow-y-auto">
                        {searchResults.map((result) => {
                            const coverUrl = result.cover?.full_url || result.cover?.thumb_url || (result.cover?.url ? `https:${result.cover.url}` : null);
                            return (
                            <div key={result.igdb_id} className="flex items-center justify-between p-2 border border-gray-200 dark:border-gray-700 rounded-lg">
                                <div className="flex items-center">
                                    {coverUrl && (
                                        <img
                                            className="w-10 h-14 object-cover rounded mr-3"
                                            src={coverUrl}
                                            alt={result.name}
                                            onError={(e) => { e.target.style.display = 'none'; }}
                                        />
                                    )}
                                    <div>
                                        <p className="text-sm font-medium text-gray-900 dark:text-white">{result.name}</p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400">IGDB ID: {result.igdb_id}</p>
                                    </div>
                                </div>
                                <Button
                                    size="small"
                                    onClick={() => resolveGame(result.igdb_id)}
                                    disabled={resolving !== null}
                                >
                                    {resolving === result.igdb_id ? 'Applico...' : 'Usa questo'}
                                </Button>
                            </div>
                            );
                        })}
                        {searchResults.length === 0 && !searching && (
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                Nessun risultato: premi Cerca per avviare la ricerca.
                            </p>
                        )}
                    </div>
                </ModalBody>
                <ModalFooter>
                    <Button layout="outline" onClick={() => setModalGame(null)}>Chiudi</Button>
                </ModalFooter>
            </Modal>
        </>
    );
};

export default VerifyGames;
