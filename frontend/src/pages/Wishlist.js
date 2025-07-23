import React, { useState, useEffect } from 'react';
import { getUserWishlist, removeGameFromWishlist, getConsoleNames } from '../services/api';
import { Card, CardBody, Button, Badge } from '@windmill/react-ui';
import { TrashIcon, HeartIcon, StarIcon, PlayIcon } from '../icons';
import ThemedSuspense from '../components/ThemedSuspense';
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@windmill/react-ui';


const Wishlist = () => {
    const [wishlist, setWishlist] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalGames, setTotalGames] = useState(0);
    const [selectedConsole, setSelectedConsole] = useState('');
    const [sortBy, setSortBy] = useState('name');
    const [sortOrder, setSortOrder] = useState('asc');
    const [searchTerm, setSearchTerm] = useState('');
    const [filteredWishlist, setFilteredWishlist] = useState([]);
    const [deleteLoading, setDeleteLoading] = useState(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [gameToDelete, setGameToDelete] = useState(null);
    const [consoleNamesCache, setConsoleNamesCache] = useState({});
    // Nuovi stati per la selezione console
    const [selectedConsoleToRemove, setSelectedConsoleToRemove] = useState(null);
    const [showConsoleSelectionModal, setShowConsoleSelectionModal] = useState(false);

    const platforms = [
        { value: '', label: 'Tutte le piattaforme' },
        { value: 'steam', label: 'Steam' },
        { value: 'psn', label: 'PlayStation Network' },
        { value: 'manual', label: 'Manuale' }
    ];

    const sortOptions = [
        { value: 'name', label: 'Nome' },
        { value: 'rating', label: 'Rating' },
        { value: 'release_date', label: 'Data di uscita' }
    ];

    // Funzione per resettare i filtri
    const resetFilters = () => {
        setSelectedConsole('');
        setSortBy('name');
        setSortOrder('asc');
        setSearchTerm('');
    };

    // Funzione per filtrare e ordinare i giochi
    const filterAndSortGames = (games) => {
        let filtered = [...games];

        // Filtra per termine di ricerca
        if (searchTerm) {
            filtered = filtered.filter(game => 
                game.name.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        // Filtra per console
        if (selectedConsole) {
            filtered = filtered.filter(game => 
                game.console && game.console.includes(parseInt(selectedConsole))
            );
        }

        // Ordina i giochi
        filtered.sort((a, b) => {
            if (sortBy === 'name') {
                return sortOrder === 'asc' 
                    ? a.name.localeCompare(b.name)
                    : b.name.localeCompare(a.name);
            } else if (sortBy === 'rating') {
                // Accedi direttamente al total_rating invece di cercare in game_details
                const ratingA = a.total_rating || 0;
                const ratingB = b.total_rating || 0;
                return sortOrder === 'asc' ? ratingA - ratingB : ratingB - ratingA;
            } else if (sortBy === 'release_date') {
                // Accedi direttamente al release_date e moltiplica per 1000 se necessario
                const dateA = a.release_date ? new Date(a.release_date * 1000).getTime() : 0;
                const dateB = b.release_date ? new Date(b.release_date * 1000).getTime() : 0;
                return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
            }
            return 0;
        });

        return filtered;
    };

    // Aggiorna la lista filtrata quando cambiano i filtri o la wishlist
    useEffect(() => {
        if (wishlist.length > 0) {
            const filtered = filterAndSortGames(wishlist);
            setFilteredWishlist(filtered);
        } else {
            setFilteredWishlist([]);
        }
    }, [wishlist, searchTerm, selectedConsole, sortBy, sortOrder]);

    // Funzione per caricare i nomi delle console
    const loadConsoleNames = async (wishlistItems) => {
        const consoleIds = [];
        
        // Raccogli tutti gli ID delle console dai giochi
        wishlistItems.forEach(item => {
            if (item.console && Array.isArray(item.console)) {
                item.console.forEach(consoleId => {
                    if (typeof consoleId === 'number' && !consoleNamesCache[consoleId]) {
                        consoleIds.push(consoleId);
                    }
                });
            }
        });
        
        // Se ci sono nuovi ID, recuperali dal database
        if (consoleIds.length > 0) {
            try {
                const uniqueIds = [...new Set(consoleIds)];
                const response = await getConsoleNames(uniqueIds);
                
                setConsoleNamesCache(prev => ({
                    ...prev,
                    ...response.console_names
                }));
            } catch (error) {
                console.error('Error loading console names:', error);
            }
        }
    };

    // Funzione per ottenere tutte le console uniche dalla wishlist
    const getUniqueConsoles = (games) => {
        const consoleSet = new Set();
        games.forEach(game => {
            if (game.console && Array.isArray(game.console)) {
                game.console.forEach(console => {
                    consoleSet.add(console);
                });
            }
        });
        return Array.from(consoleSet);
    };

    // Stato per le console disponibili
    const [availableConsoles, setAvailableConsoles] = useState([]);

    // Aggiorna le console disponibili quando cambia la wishlist
    useEffect(() => {
        const consoles = wishlist.length > 0 ? getUniqueConsoles(wishlist) : [];
        setAvailableConsoles(consoles);
        if (consoles.length > 0) {
            loadConsoleNames(wishlist);
        }
    }, [wishlist]);

    const fetchWishlist = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const params = {
                page: currentPage,
                limit: 20,
                sort_by: sortBy,
                sort_order: sortOrder
            };

            if (selectedConsole) {
                params.platform = selectedConsole;
            }

            const data = await getUserWishlist(params);
            // Il backend restituisce { wishlist: [...] } invece di { games: [...] }
            const wishlistArray = data.wishlist || data.games || [];
            setWishlist(wishlistArray);
            setTotalPages(data.total_pages || 1);
            setTotalGames(data.total_games || data.wishlist?.length || 0);
            
            // Carica i nomi delle console
            await loadConsoleNames(wishlistArray);
        } catch (err) {
            console.error('Error fetching wishlist:', err);
            setError(err.message || 'Errore nel caricamento della wishlist');
        } finally {
            setLoading(false);
        }
    };

    // Effettua il fetch quando cambiano i parametri di paginazione o filtri
    useEffect(() => {
        fetchWishlist();
    }, [currentPage, selectedConsole, sortBy, sortOrder]);

    const handleDeleteGame = async () => {
        if (!gameToDelete) return;

        try {
            setDeleteLoading(gameToDelete.wishlist_id || gameToDelete._id);
            let shouldResetFilter = false;
            
            // Se è stata selezionata una console specifica, rimuovi solo quella console
            if (selectedConsoleToRemove) {
                await removeGameFromWishlist(gameToDelete.game_id, selectedConsoleToRemove);
                
                // Controlla se ci sono altri giochi con la console selezionata nel filtro attuale
                const remainingGamesWithFilteredConsole = wishlist.filter(game => {
                    // Se è lo stesso gioco che stiamo modificando, controlliamo le console rimanenti
                    if (game._id === gameToDelete._id) {
                        const remainingConsoles = game.console.filter(c => c !== selectedConsoleToRemove);
                        return remainingConsoles.includes(parseInt(selectedConsole));
                    }
                    // Per gli altri giochi, controlliamo normalmente
                    return game.console && game.console.includes(parseInt(selectedConsole));
                });

                // Se non ci sono più giochi con la console del filtro attuale
                if (remainingGamesWithFilteredConsole.length === 0 && selectedConsole) {
                    shouldResetFilter = true;
                }
            } else {
                // Rimuovi l'intero gioco
                await removeGameFromWishlist(gameToDelete.game_id, null);
                
                // Se questo era l'ultimo gioco con la console filtrata, resetta il filtro
                const remainingGamesWithFilteredConsole = wishlist.filter(game => 
                    game._id !== gameToDelete._id && 
                    game.console && 
                    game.console.includes(parseInt(selectedConsole))
                );
                
                if (remainingGamesWithFilteredConsole.length === 0 && selectedConsole) {
                    shouldResetFilter = true;
                }
            }
            
            // Reset UI state
            setShowDeleteModal(false);
            setShowConsoleSelectionModal(false);
            setGameToDelete(null);
            setSelectedConsoleToRemove(null);

            // Se dobbiamo resettare il filtro, lo facciamo prima di ricaricare i dati
            if (shouldResetFilter) {
                setSelectedConsole('');
                setCurrentPage(1);
                
                // Forza il refresh immediato con tutti i giochi
                const data = await getUserWishlist({
                    page: 1,
                    limit: 20,
                    sort_by: sortBy,
                    sort_order: sortOrder
                });
                
                setWishlist(data.wishlist || data.games || []);
                setTotalPages(data.total_pages || 1);
                setTotalGames(data.total_games || data.wishlist?.length || 0);
            } else {
                // Altrimenti, usa i parametri correnti
                const params = {
                    page: currentPage,
                    limit: 20,
                    sort_by: sortBy,
                    sort_order: sortOrder,
                    ...(selectedConsole && { platform: selectedConsole })
                };
                
                const data = await getUserWishlist(params);
                setWishlist(data.wishlist || data.games || []);
                setTotalPages(data.total_pages || 1);
                setTotalGames(data.total_games || data.wishlist?.length || 0);
            }

        } catch (err) {
            console.error('Error removing game from wishlist:', err);
            alert(err.message || 'Errore nella rimozione del gioco');
        } finally {
            setDeleteLoading(null);
        }
    };

    const confirmDelete = (game) => {
        setGameToDelete(game);
        
        // Se il gioco ha più console, mostra il modal di selezione console
        if (game.console && game.console.length > 1) {
            setShowConsoleSelectionModal(true);
        } else {
            // Se ha una sola console o nessuna, mostra direttamente il modal di conferma
            setShowDeleteModal(true);
        }
    };

    const handleConsoleSelection = (consoleId) => {
        setSelectedConsoleToRemove(consoleId);
        setShowConsoleSelectionModal(false);
        setShowDeleteModal(true);
    };

    const handleRemoveAllConsoles = () => {
        setSelectedConsoleToRemove(null);
        setShowConsoleSelectionModal(false);
        setShowDeleteModal(true);
    };

    const getPlatformIcon = (platform) => {
        if (!platform) return '🎲';
        
        switch (platform.toLowerCase()) {
            case 'steam':
                return '🎮';
            case 'psn':
                return '🎯';
            case 'manual':
                return '✏️';
            default:
                return '🎲';
        }
    };

    const getPlatformType = (platform) => {
        if (!platform) return 'default';
        
        switch (platform.toLowerCase()) {
            case 'steam':
                return 'success';
            case 'psn':
                return 'warning';
            case 'manual':
                return 'info';
            default:
                return 'default';
        }
    };

    const getConsoleName = (consoleCode) => {
        // Se consoleCode è già una stringa (nome console), restituiscilo direttamente
        if (typeof consoleCode === 'string') {
            return consoleCode
        }
        
        // Se è un numero (ID console), controlla la cache
        if (consoleNamesCache[consoleCode]) {
            return consoleNamesCache[consoleCode]
        }
        
        // Se non è in cache, restituisci un fallback
        return `Console ${consoleCode}`;
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('it-IT');
    };

    const formatRating = (rating) => {
        if (!rating) return 'N/A';
        return `${rating}/100`;
    };

    // Modifica la funzione che gestisce il cambio del campo di ordinamento
    const handleSortChange = (newSortBy) => {
        if (newSortBy === sortBy) {
            // Se clicchiamo sullo stesso campo, invertiamo l'ordine
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            // Se cambiamo campo, impostiamo l'ordine di default in base al campo
            setSortBy(newSortBy);
            if (newSortBy === 'rating' || newSortBy === 'release_date') {
                setSortOrder('desc'); // Dal più alto/recente al più basso/vecchio
            } else {
                setSortOrder('asc'); // Ordine alfabetico per il nome
            }
        }
    };

    if (loading) {
        return <ThemedSuspense />;
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <div className="container mx-auto px-6 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                        La Mia Wishlist
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Gestisci i giochi che desideri acquistare
                    </p>
                </div>

                {/* Stats Card */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                    <Card>
                        <CardBody>
                            <div className="flex items-center">
                                <div className="p-3 rounded-full bg-red-100 dark:bg-red-900">
                                    <HeartIcon className="h-6 w-6 text-red-600 dark:text-red-400" />
                                </div>
                                <div className="ml-4">
                                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                                        Totale Giochi
                                    </p>
                                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                                        {totalGames}
                                    </p>
                                </div>
                            </div>
                        </CardBody>
                    </Card>
                </div>

                {/* Filters */}
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 mb-8">
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                        {/* Search Field */}
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Cerca gioco
                            </label>
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Digita il nome del gioco..."
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                            />
                        </div>

                        {/* Console Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Console
                            </label>
                            <select
                                value={selectedConsole}
                                onChange={(e) => setSelectedConsole(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                            >
                                <option value="">Tutte le console</option>
                                {availableConsoles.map((console) => (
                                    <option key={console} value={console}>
                                        {getConsoleName(console)}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Sort By */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Ordina per
                            </label>
                            <select
                                value={sortBy}
                                onChange={(e) => handleSortChange(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                            >
                                {sortOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Sort Order */}
                        {/* <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Ordine
                            </label>
                            <select
                                value={sortOrder}
                                onChange={(e) => setSortOrder(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                            >
                                <option value="asc">Crescente</option>
                                <option value="desc">Decrescente</option>
                            </select>
                        </div> */}

                        {/* Action Buttons */}
                        <div className="md:col-span-5 flex justify-end space-x-4">
                            <Button
                                onClick={resetFilters}
                                layout="outline"
                            >
                                Reset Filtri
                            </Button>
                            <Button
                                onClick={fetchWishlist}
                            >
                                Aggiorna
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 mb-6">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                                    Errore
                                </h3>
                                <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                                    {error}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Games List */}
                {filteredWishlist.length === 0 ? (
                    <div className="text-center py-12">
                        <HeartIcon className="mx-auto h-12 w-12 text-gray-400" />
                        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
                            Nessun gioco nella wishlist
                        </h3>
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                            Inizia ad aggiungere giochi dalla pagina di ricerca!
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredWishlist.map((wishlistItem) => {
                            const coverUrl = wishlistItem.cover_image ? `https:${wishlistItem.cover_image}` : null;
                            
                            return (
                                <Card key={wishlistItem._id} className="hover:shadow-lg transition-shadow duration-200">
                                    <CardBody>
                                        <div className="flex justify-between items-start">
                                            <div className="w-full text-center">
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                                    {wishlistItem.name}
                                                </h3>
                                            </div>
                                            <Button
                                                onClick={() => confirmDelete(wishlistItem)}
                                                disabled={deleteLoading === (wishlistItem.wishlist_id || wishlistItem._id)}
                                                className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 ml-2"
                                            >
                                                {deleteLoading === (wishlistItem.wishlist_id || wishlistItem._id) ? (
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                                                ) : (
                                                    <TrashIcon className="h-4 w-4" />
                                                )}
                                            </Button>
                                        </div>

                                        {coverUrl && (
                                            <div className="my-4 flex justify-center">
                                                <div className="relative w-48 h-64">
                                                    <img
                                                        src={coverUrl}
                                                        alt={wishlistItem.name}
                                                        className="w-full h-full object-cover rounded-lg bg-gray-100 dark:bg-gray-700"
                                                        onError={(e) => {
                                                            e.target.style.display = 'none'
                                                            // Mostra un'icona di fallback
                                                            const fallbackIcon = document.createElement('div')
                                                            fallbackIcon.className = 'w-full h-full flex items-center justify-center bg-gray-200 dark:bg-gray-700 rounded-lg'
                                                            fallbackIcon.innerHTML = '<svg class="w-12 h-12 text-gray-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path></svg>'
                                                            e.target.parentNode.appendChild(fallbackIcon)
                                                        }}
                                                    />
                                                </div>
                                            </div>
                                        )}
                                        
                                        <div className="flex flex-col space-y-4 mt-4">
                                            {/* Descrizione del gioco */}
                                            {wishlistItem.description && (
                                                <div className="text-sm text-gray-600 dark:text-gray-400">
                                                    <p className="line-clamp-3 text-center">
                                                        {wishlistItem.description}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Rating */}
                                            {wishlistItem.total_rating && (
                                                <div className="flex items-center justify-center">
                                                    <StarIcon className="h-5 w-5 text-yellow-500 mr-2" />
                                                    <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                                                        {Math.round(wishlistItem.total_rating)}/100
                                                    </span>
                                                </div>
                                            )}

                                            {/* Console badges */}
                                            <div className="flex items-center justify-center">
                                                {wishlistItem.console && wishlistItem.console.length > 0 && (
                                                    <div className="flex flex-wrap gap-1">
                                                        {wishlistItem.console.map((consoleId, idx) => (
                                                            <Badge key={idx} type="success">
                                                                {getConsoleName(consoleId)}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            
                                            {/* Data di uscita */}
                                            {wishlistItem.release_date && (
                                                <div className="flex items-center justify-center">
                                                    <PlayIcon className="h-4 w-4 text-blue-500 mr-2" />
                                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                                        Uscita: {formatDate(wishlistItem.release_date * 1000)}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    </CardBody>
                                </Card>
                        );
                        })}
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="mt-8 flex justify-center">
                        <nav className="flex items-center space-x-2">
                            <Button
                                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                                disabled={currentPage === 1}
                                size="small"
                            >
                                Precedente
                            </Button>
                            
                            <span className="px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
                                Pagina {currentPage} di {totalPages}
                            </span>
                            
                            <Button
                                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                                disabled={currentPage === totalPages}
                                size="small"
                            >
                                Successiva
                            </Button>
                        </nav>
                    </div>
                )}
            </div>

            {/* Console Selection Modal */}
            {showConsoleSelectionModal && (
                <Modal isOpen={showConsoleSelectionModal} onClose={() => setShowConsoleSelectionModal(false)}>
                    <ModalHeader className="text-center">
                        Rimuovi console specifica
                    </ModalHeader>
                    <ModalBody>
                        {gameToDelete && (
                            <div>
                                <p className="mb-4 text-gray-600 dark:text-gray-400 text-center">
                                    Seleziona la console da rimuovere per <strong>{gameToDelete.name}</strong>:
                                </p>
                                <div className="flex flex-col space-y-2 mb-6">
                                    {gameToDelete.console && gameToDelete.console.length > 0 && (
                                        gameToDelete.console.map((consoleId, index) => (
                                            <Button
                                                key={index}
                                                onClick={() => handleConsoleSelection(consoleId)}
                                                layout="outline"
                                                className="w-full text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                                            >
                                                {getConsoleName(consoleId)}
                                            </Button>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </ModalBody>
                    <ModalFooter className="flex justify-center">
                        <Button
                            onClick={() => handleRemoveAllConsoles()}
                            layout="outline"
                            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                        >
                            Rimuovi tutte le console
                        </Button>
                    </ModalFooter>
                </Modal>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <Modal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)}>
                    <ModalHeader className="text-center justify-center">
                        Conferma Eliminazione
                    </ModalHeader>
                    <ModalBody>
                        {gameToDelete && (
                            <p className="text-center">
                                {selectedConsoleToRemove ? 
                                    `Sei sicuro di voler rimuovere "${gameToDelete.name}" dalla wishlist per ${getConsoleName(selectedConsoleToRemove)}?` :
                                    `Sei sicuro di voler rimuovere "${gameToDelete.name}" dalla tua wishlist?`
                                }
                                <br />
                                <span className="text-sm text-gray-500 dark:text-gray-400 mt-2 block">
                                    Questa azione non può essere annullata.
                                </span>
                            </p>
                        )}
                    </ModalBody>
                    <ModalFooter className="flex justify-center">
                        <div className="hidden sm:block">
                            <Button onClick={handleDeleteGame} className="bg-red-600 hover:bg-red-700">
                                Elimina
                            </Button>
                        </div>
                        <div className="block w-full sm:hidden">
                            <Button block size="large" onClick={handleDeleteGame} className="bg-red-600 hover:bg-red-700">
                                Elimina
                            </Button>
                        </div>
                    </ModalFooter>
                </Modal>
            )}
        </div>
    );
};

export default Wishlist; 