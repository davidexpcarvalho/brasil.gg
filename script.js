const playerStatisticsJsonUrl = 'https://davidexpcarvalho.github.io/brasil.gg/player_statistics_rows.json';
const underperformingPositionsJsonUrl = 'https://davidexpcarvalho.github.io/brasil.gg/underperforming_positions_rows.json';

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch data from ${url}`);
    return response.json();
}

function formatNumber(value) {
    return Number(value).toFixed(1);
}

function createTableHtml(data, headers, fieldMap) {
    if (data.length === 0) {
        return '<p>Nenhum dado disponível.</p>';
    }

    let tableHtml = '<table><thead><tr>';
    headers.forEach(header => {
        tableHtml += `<th>${header}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';

    data.forEach(row => {
        tableHtml += '<tr>';
        headers.forEach(header => {
            const field = fieldMap[header];
            let value = row[field] !== undefined ? row[field] : 'N/A';
            if (typeof value === 'number') {
                value = formatNumber(value);
            }
            if (field === 'win_rate' || field === 'desempenho') {
                value = value !== 'N/A' ? `${formatNumber(value * 100)}%` : value;
            }
            tableHtml += `<td>${value}</td>`;
        });
        tableHtml += '</tr>';
    });

    tableHtml += '</tbody></table>';
    return tableHtml;
}

async function createPlayerPages() {
    try {
        const [playerStatistics, underperformingPositions] = await Promise.all([
            fetchJson(playerStatisticsJsonUrl),
            fetchJson(underperformingPositionsJsonUrl)
        ]);

        const groupedPlayerStats = groupBy(playerStatistics, 'player_name');
        const groupedUnderperformingPositions = groupBy(underperformingPositions, 'player_name');

        const allPlayers = new Set([
            ...Object.keys(groupedPlayerStats),
            ...Object.keys(groupedUnderperformingPositions),
        ]);

        const dropdown = document.getElementById('dropdown');

        allPlayers.forEach(player => {
            const playerFileName = `player_${player.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
            const playerStats = groupedPlayerStats[player] || [];
            const playerUnderperforming = groupedUnderperformingPositions[player] || [];

            const playerPage = document.createElement('div');
            playerPage.id = playerFileName;
            playerPage.classList.add('player-page');
            playerPage.style.display = 'none';
            playerPage.innerHTML = `
                <h1>Análise do Jogador ${player}</h1>
                <button id="back-button" onclick="showSearch()">Voltar</button>
                <div class="container">
                    <h2>Estatísticas do Jogador</h2>
                    ${createTableHtml(playerStats, ['Campeão', 'Jogos Jogados', 'Vitórias', 'Taxa de Vitórias'], {
                        'Campeão': 'champion',
                        'Jogos Jogados': 'games_played',
                        'Vitórias': 'wins',
                        'Taxa de Vitórias': 'win_rate'
                    })}
                </div>
                <div class="container">
                    <h2>Posições de Desempenho Inferior</h2>
                    ${createTableHtml(playerUnderperforming, ['Posição', 'Estatística', 'Média do Jogador', 'Média da Posição'], {
                        'Posição': 'position',
                        'Estatística': 'stat',
                        'Média do Jogador': 'player_avg',
                        'Média da Posição': 'position_avg'
                    })}
                </div>
            `;
            document.body.appendChild(playerPage);

            const dropdownItem = document.createElement('div');
            dropdownItem.classList.add('dropdown-item');
            dropdownItem.textContent = player;
            dropdownItem.setAttribute('role', 'option');
            dropdownItem.setAttribute('aria-selected', 'false');
            dropdownItem.onclick = () => {
                showPlayerPage(playerFileName);
                document.querySelectorAll('.dropdown-item').forEach(item => item.setAttribute('aria-selected', 'false'));
                dropdownItem.setAttribute('aria-selected', 'true');
            };
            dropdown.appendChild(dropdownItem);
        });
    } catch (error) {
        console.error("Error creating player pages:", error);
    }
}

function groupBy(array, key) {
    return array.reduce((acc, obj) => {
        const keyValue = obj[key];
        if (!acc[keyValue]) {
            acc[keyValue] = [];
        }
        acc[keyValue].push(obj);
        return acc;
    }, {});
}

function showPlayerPage(playerFileName) {
    document.querySelectorAll('.player-page').forEach(page => page.style.display = 'none');
    document.getElementById(playerFileName).style.display = 'block';
    document.getElementById('search-container').style.display = 'none';
}

function showSearch() {
    document.querySelectorAll('.player-page').forEach(page => page.style.display = 'none');
    document.getElementById('search-container').style.display = 'block';
}

function filterPlayers() {
    const searchInput = document.getElementById('search-input').value.toLowerCase();
    const dropdown = document.getElementById('dropdown');
    const dropdownItems = dropdown.querySelectorAll('.dropdown-item');
    let hasResults = false;

    dropdownItems.forEach(item => {
        if (item.textContent.toLowerCase().includes(searchInput)) {
            item.style.display = 'block';
            hasResults = true;
        } else {
            item.style.display = 'none';
        }
    });

    dropdown.setAttribute('aria-expanded', hasResults);
}

document.getElementById('search-input').addEventListener('input', filterPlayers);

createPlayerPages().then(() => console.log('Páginas dos jogadores geradas com sucesso.'));
