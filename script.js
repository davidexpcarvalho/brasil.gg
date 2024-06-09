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

function createTableHtml(data, headers, fieldMap, pageSize, currentPage, sortable = false) {
    if (data.length === 0) {
        return '<p>Nenhum dado disponível.</p>';
    }

    let tableHtml = '<table><thead><tr>';
    headers.forEach(header => {
        tableHtml += `<th${sortable ? ` class="sortable" onclick="sortTable('${header}', '${currentPage}')"` : ''}>${header}</th>`;
    });
    tableHtml += '</tr></thead><tbody>';

    const start = pageSize * (currentPage - 1);
    const end = start + pageSize;
    const paginatedData = data.slice(start, end);

    paginatedData.forEach(row => {
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

function createPaginationControls(data, pageSize, currentPage, containerId, updatePageFunction) {
    const totalPages = Math.ceil(data.length / pageSize);
    let paginationHtml = '<div class="pagination">';

    for (let i = 1; i <= totalPages; i++) {
        paginationHtml += `<button ${i === currentPage ? 'class="active"' : ''} onclick="${updatePageFunction.name}(${i})">${i}</button>`;
    }

    paginationHtml += '</div>';
    document.getElementById(containerId).innerHTML = paginationHtml;
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
            const playerFileName = `player_${player.replace(/[^a-zA-Z0-9]/g, '_')}`;
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
                    <div id="${playerFileName}_stats"></div>
                    <div id="${playerFileName}_stats_pagination"></div>
                </div>
                <div class="container">
                    <h2>Posições de Desempenho Inferior</h2>
                    <div id="${playerFileName}_underperforming"></div>
                    <div id="${playerFileName}_underperforming_pagination"></div>
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

                // Inicializar paginação e ordenação
                initializeTablePaginationAndSorting(playerStats, playerFileName, 'stats', ['Campeão', 'Jogos Jogados', 'Vitórias', 'Taxa de Vitórias'], {
                    'Campeão': 'champion',
                    'Jogos Jogados': 'games_played',
                    'Vitórias': 'wins',
                    'Taxa de Vitórias': 'win_rate'
                });

                initializeTablePaginationAndSorting(playerUnderperforming, playerFileName, 'underperforming', ['Posição', 'Estatística', 'Média do Jogador', 'Média da Posição'], {
                    'Posição': 'position',
                    'Estatística': 'stat',
                    'Média do Jogador': 'player_avg',
                    'Média da Posição': 'position_avg'
                });
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

    dropdown.style.display = hasResults ? 'block' : 'none';
    dropdown.setAttribute('aria-expanded', hasResults);
}

function initializeTablePaginationAndSorting(data, playerFileName, tableId, headers, fieldMap, pageSize = 10) {
    let currentPage = 1;

    const updateTable = (page) => {
        currentPage = page;
        document.getElementById(`${playerFileName}_${tableId}`).innerHTML = createTableHtml(data, headers, fieldMap, pageSize, currentPage, true);
        createPaginationControls(data, pageSize, currentPage, `${playerFileName}_${tableId}_pagination`, updateTable);
    };

    updateTable(1);
}

function sortTable(header, currentPage) {
    const playerFileName = document.querySelector('.player-page:not([style*="display: none"])').id;
    const tableId = `${playerFileName}_stats`;
    const table = document.getElementById(tableId);
    const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent);
    const index = headers.indexOf(header);

    let data = [];
    table.querySelectorAll('tbody tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        data.push(Array.from(cells).map(cell => cell.textContent));
    });

    const isAscending = table.getAttribute('data-sort-asc') === 'true';
    data.sort((a, b) => {
        let valA = a[index];
        let valB = b[index];
        if (valA.endsWith('%')) {
            valA = parseFloat(valA.replace('%', '')) / 100;
            valB = parseFloat(valB.replace('%', '')) / 100;
        }
        if (isNaN(valA)) {
            return isAscending ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return isAscending ? valA - valB : valB - valA;
    });

    table.setAttribute('data-sort-asc', !isAscending);
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    data.forEach(rowData => {
        const row = document.createElement('tr');
        rowData.forEach(cellData => {
            const cell = document.createElement('td');
            cell.textContent = cellData;
            row.appendChild(cell);
        });
        tbody.appendChild(row);
    });

    // Atualizar paginação
    const headersMap = {
        'Campeão': 'champion',
        'Jogos Jogados': 'games_played',
        'Vitórias': 'wins',
        'Taxa de Vitórias': 'win_rate'
    };
    initializeTablePaginationAndSorting(data.map(row => {
        let obj = {};
        headers.forEach((header, idx) => {
            let value = row[idx];
            if (value.endsWith('%')) {
                value = parseFloat(value.replace('%', '')) / 100;
            }
            obj[headersMap[header]] = isNaN(value) ? value : parseFloat(value);
        });
        return obj;
    }), playerFileName, 'stats', headers, headersMap, 10);
}

document.getElementById('search-input').addEventListener('input', filterPlayers);

createPlayerPages().then(() => console.log('Páginas dos jogadores geradas com sucesso.'));
