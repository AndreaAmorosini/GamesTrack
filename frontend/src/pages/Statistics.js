import React, { useState, useEffect } from 'react';
import PageTitle from '../components/Typography/PageTitle';
import { Card, CardBody } from '@windmill/react-ui';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import ChartLegend from '../components/Chart/ChartLegend';
import InfoCard from '../components/Cards/InfoCard';
import RoundIcon from '../components/RoundIcon';
import { TrophyIcon, GamesIcon, PlayIcon } from '../icons';
import GameNameLink from '../components/GameNameLink';
import { getUserStatistics } from '../services/api';
import { CardSkeletonGrid } from '../components/Skeletons';
import { useToast } from '../context/ToastContext';

const PLATFORM_LABELS = {
    steam: 'Steam',
    psn: 'PlayStation Network',
    retroachievements: 'RetroAchievements',
    gog: 'GOG',
};

const Statistics = () => {
    const { notify } = useToast();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                setStats(await getUserStatistics());
            } catch (err) {
                notify(err.message || 'Errore nel caricamento delle statistiche', 'error');
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    if (loading) {
        return (
            <>
                <PageTitle>Statistiche</PageTitle>
                <CardSkeletonGrid count={4} />
            </>
        );
    }

    if (!stats) {
        return (
            <>
                <PageTitle>Statistiche</PageTitle>
                <p className="text-gray-600 dark:text-gray-400">Nessuna statistica disponibile.</p>
            </>
        );
    }

    const progression = stats.trophy_progression || [];
    const platformBreakdown = stats.platform_breakdown || [];
    const topGames = stats.top_games || [];

    const totalTrophies = platformBreakdown.reduce((sum, p) => sum + (p.trophies || 0), 0);
    const totalGames = platformBreakdown.reduce((sum, p) => sum + (p.games || 0), 0);
    const totalHours = Math.round(platformBreakdown.reduce((sum, p) => sum + (p.play_count || 0), 0) / 60);

    const progressionOptions = {
        data: {
            labels: progression.map(p => p.date),
            datasets: [
                {
                    label: 'Trofei totali',
                    data: progression.map(p => p.total_trophies),
                    fill: false,
                    borderColor: '#7e3af2',
                    tension: 0.4,
                },
                {
                    label: 'Ore di gioco totali',
                    data: progression.map(p => Math.round(p.total_play_count / 60)),
                    fill: false,
                    borderColor: '#1c64f2',
                    tension: 0.4,
                },
            ],
        },
        options: { responsive: true, legend: { display: true } },
    };

    const platformOptions = {
        data: {
            labels: platformBreakdown.map(p => PLATFORM_LABELS[p._id] || p._id),
            datasets: [
                {
                    label: 'Trofei',
                    data: platformBreakdown.map(p => p.trophies),
                    backgroundColor: ['#0694a2', '#1c64f2', '#e3a008', '#d64794', '#7e3af2'],
                },
            ],
        },
        options: { responsive: true, legend: { display: false } },
    };

    const gamesDoughnut = {
        data: {
            labels: platformBreakdown.map(p => PLATFORM_LABELS[p._id] || p._id),
            datasets: [
                {
                    data: platformBreakdown.map(p => p.games),
                    backgroundColor: ['#0694a2', '#1c64f2', '#e3a008', '#d64794', '#7e3af2'],
                },
            ],
        },
        options: { responsive: true, cutoutPercentage: 70, legend: { display: false } },
    };

    return (
        <>
            <PageTitle>Statistiche</PageTitle>

            {/* Cards totali */}
            <div className="grid gap-6 mb-8 md:grid-cols-3">
                <InfoCard title="Giochi in libreria" value={totalGames}>
                    <RoundIcon icon={GamesIcon} iconColorClass="text-orange-500 dark:text-orange-100" bgColorClass="bg-orange-100 dark:bg-orange-500" className="mr-4" />
                </InfoCard>
                <InfoCard title="Trofei/Achievement" value={totalTrophies}>
                    <RoundIcon icon={TrophyIcon} iconColorClass="text-green-500 dark:text-green-100" bgColorClass="bg-green-100 dark:bg-green-500" className="mr-4" />
                </InfoCard>
                <InfoCard title="Ore di Gioco" value={totalHours}>
                    <RoundIcon icon={PlayIcon} iconColorClass="text-blue-500 dark:text-blue-100" bgColorClass="bg-blue-100 dark:bg-blue-500" className="mr-4" />
                </InfoCard>
            </div>

            {/* Progressione nel tempo */}
            <Card className="mb-8">
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Progressione nel tempo</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        I totali crescono a ogni sincronizzazione (lo storico parte dal primo sync con questa funzione attiva)
                    </p>
                </div>
                <CardBody>
                    {progression.length >= 2 ? (
                        <Line {...progressionOptions} />
                    ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                            Servono almeno due sincronizzazioni per tracciare una progressione.
                        </p>
                    )}
                </CardBody>
            </Card>

            {/* Ripartizione piattaforme */}
            <div className="grid gap-6 mb-8 md:grid-cols-2">
                <Card>
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Trofei per piattaforma</h3>
                    </div>
                    <CardBody>
                        <Bar {...platformOptions} />
                    </CardBody>
                </Card>
                <Card>
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Giochi per piattaforma</h3>
                    </div>
                    <CardBody>
                        <Doughnut {...gamesDoughnut} />
                        <ChartLegend
                            legends={platformBreakdown.map((p, i) => ({
                                title: PLATFORM_LABELS[p._id] || p._id,
                                color: gamesDoughnut.data.datasets[0].backgroundColor[i % 5],
                            }))}
                        />
                    </CardBody>
                </Card>
            </div>

            {/* Top giochi */}
            <Card className="mb-8">
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Top 10 giochi per trofei</h3>
                </div>
                <CardBody>
                    <ol className="space-y-2">
                        {topGames.map((g, i) => (
                            <li key={g.game_id} className="flex items-center justify-between text-sm border-b border-gray-100 dark:border-gray-700 pb-2">
                                <span className="flex items-center">
                                    <span className="w-6 text-gray-400 font-semibold">{i + 1}.</span>
                                    <GameNameLink name={g.name} gameId={g.game_id} />
                                </span>
                                <span className="text-gray-500 dark:text-gray-400">
                                    {g.num_trophies || 0} trofei · {Math.round((g.play_count || 0) / 60)}h
                                </span>
                            </li>
                        ))}
                        {topGames.length === 0 && (
                            <li className="text-gray-500 dark:text-gray-400">Nessun dato disponibile</li>
                        )}
                    </ol>
                </CardBody>
            </Card>
        </>
    );
};

export default Statistics;
