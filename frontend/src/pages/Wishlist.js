import React, { useState, useEffect } from 'react';
import { getUserWishlist, removeGameFromWishlist } from '../services/api';
import { Card, CardBody, Button, Badge } from '@windmill/react-ui';
import { TrashIcon, HeartIcon, StarIcon, PlayIcon } from '../icons';
import ThemedSuspense from '../components/ThemedSuspense';


const Wishlist = () => {
    const [wishlist, setWishlist] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalGames, setTotalGames] = useState(0);
    const [selectedPlatform, setSelectedPlatform] = useState('');
    const [sortBy, setSortBy] = useState('name');
    const [sortOrder, setSortOrder] = useState('asc');
    const [deleteLoading, setDeleteLoading] = useState(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [gameToDelete, setGameToDelete] = useState(null);

    const platforms = [
        { value: '', label: 'Tutte le piattaforme' },
        { value: 'steam', label: 'Steam' },
        { value: 'psn', label: 'PlayStation Network' },
        { value: 'manual', label: 'Manuale' }
    ];

    const sortOptions = [
        { value: 'name', label: 'Nome' },
        { value: 'platform', label: 'Piattaforma' },
        { value: 'rating', label: 'Rating' },
        { value: 'release_date', label: 'Data di uscita' }
    ];

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

            if (selectedPlatform) {
                params.platform = selectedPlatform;
            }

            const data = await getUserWishlist(params);
            // Il backend restituisce { wishlist: [...] } invece di { games: [...] }
            setWishlist(data.wishlist || data.games || []);
            setTotalPages(data.total_pages || 1);
            setTotalGames(data.total_games || data.wishlist?.length || 0);
        } catch (err) {
            console.error('Error fetching wishlist:', err);
            setError(err.message || 'Errore nel caricamento della wishlist');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWishlist();
    }, [currentPage, selectedPlatform, sortBy, sortOrder]);

    const handleDeleteGame = async () => {
        if (!gameToDelete) return;

        try {
            setDeleteLoading(gameToDelete._id);
            // Passa il game_id (che ora è sempre una stringa)
            await removeGameFromWishlist(gameToDelete.game_id, gameToDelete.platform);
            
            alert('Gioco rimosso dalla wishlist con successo!');
            setShowDeleteModal(false);
            setGameToDelete(null);
            fetchWishlist(); // Ricarica la lista
        } catch (err) {
            console.error('Error removing game from wishlist:', err);
            alert(err.message || 'Errore nella rimozione del gioco');
        } finally {
            setDeleteLoading(null);
        }
    };

    const confirmDelete = (game) => {
        setGameToDelete(game);
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

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('it-IT');
    };

    const formatRating = (rating) => {
        if (!rating) return 'N/A';
        return `${rating}/100`;
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
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {/* Platform Filter */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Piattaforma
                            </label>
                            <select
                                value={selectedPlatform}
                                onChange={(e) => setSelectedPlatform(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                            >
                                {platforms.map((platform) => (
                                    <option key={platform.value} value={platform.value}>
                                        {platform.label}
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
                                onChange={(e) => setSortBy(e.target.value)}
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
                        <div>
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
                        </div>

                        {/* Refresh Button */}
                        <div className="flex items-end">
                            <Button
                                onClick={fetchWishlist}
                                size="small"
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
                {wishlist.length === 0 ? (
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
                        {wishlist.map((wishlistItem) => {
                            // Estrai i dettagli del gioco dal game_details
                            const gameDetails = wishlistItem.game_details?.[0] || {};
                            const game = {
                                ...wishlistItem,
                                name: gameDetails.name || wishlistItem.name,
                                rating: gameDetails.total_rating,
                                release_date: gameDetails.release_date,
                                summary: gameDetails.description,
                                cover_url: gameDetails.cover_image ? `https:${gameDetails.cover_image}` : null
                            };
                            
                            return (
                                <Card key={wishlistItem._id} className="hover:shadow-lg transition-shadow duration-200">
                                    <CardBody>
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                                    {game.name}
                                                </h3>
                                                <div className="flex items-center mt-2">
                                                    <Badge type={getPlatformType(wishlistItem.platform)}>
                                                        {getPlatformIcon(wishlistItem.platform)} {wishlistItem.platform || 'N/A'}
                                                    </Badge>
                                                </div>
                                            </div>
                                        <Button
                                            onClick={() => confirmDelete(wishlistItem)}
                                            disabled={deleteLoading === (wishlistItem.wishlist_id || wishlistItem._id)}
                                            className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                                        >
                                            {deleteLoading === (wishlistItem.wishlist_id || wishlistItem._id) ? (
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                                            ) : (
                                                <TrashIcon className="h-4 w-4" />
                                            )}
                                        </Button>
                                    </div>
                                    <div className="space-y-3">
                                        {game.cover_url && (
                                            <div className="aspect-w-16 aspect-h-9 mb-4">
                                                <img
                                                    src={game.cover_url}
                                                    alt={game.name}
                                                    className="w-full h-32 object-cover rounded-lg"
                                                />
                                            </div>
                                        )}
                                        
                                        <div className="space-y-2">
                                            {game.rating && (
                                                <div className="flex items-center">
                                                    <StarIcon className="h-4 w-4 text-yellow-500 mr-2" />
                                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                                        Rating: {formatRating(game.rating)}
                                                    </span>
                                                </div>
                                            )}
                                            
                                            {game.release_date && (
                                                <div className="flex items-center">
                                                    <PlayIcon className="h-4 w-4 text-blue-500 mr-2" />
                                                    <span className="text-sm text-gray-600 dark:text-gray-400">
                                                        Uscita: {formatDate(game.release_date)}
                                                    </span>
                                                </div>
                                            )}
                                            
                                            {game.summary && (
                                                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                                                    {game.summary}
                                                </p>
                                            )}
                                        </div>
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

            {/* Delete Confirmation Modal */}
            {showDeleteModal && (
                <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                    <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white dark:bg-gray-800">
                        <div className="mt-3 text-center">
                            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 dark:bg-red-900">
                                <TrashIcon className="h-6 w-6 text-red-600 dark:text-red-400" />
                            </div>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mt-4">
                                Rimuovi dalla wishlist
                            </h3>
                            <div className="mt-2 px-7 py-3">
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Sei sicuro di voler rimuovere "{gameToDelete?.name}" dalla tua wishlist?
                                    Questa azione non può essere annullata.
                                </p>
                            </div>
                            <div className="flex justify-center space-x-4 mt-4">
                                <Button
                                    onClick={() => setShowDeleteModal(false)}
                                    layout="outline"
                                >
                                    Annulla
                                </Button>
                                <Button
                                    onClick={handleDeleteGame}
                                    layout="danger"
                                >
                                    Rimuovi
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Wishlist; 