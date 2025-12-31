const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const newConversationBtn = document.getElementById('newConversationBtn');

let conversationHistory = [];


sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
newConversationBtn.addEventListener('click', startNewConversation);

function startNewConversation() {
    chatContainer.innerHTML = '';

    conversationHistory = [];


    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
        <h2>Welcome! 👋</h2>
        <p>I'm here to help you find advisors based on your research interests.</p>
        <p>Ask me about any research topic or field, and I'll help you discover potential advisors!</p>
    `;
    chatContainer.appendChild(welcomeDiv);

    messageInput.value = '';

    messageInput.focus();
}

async function sendMessage() {
    const message = messageInput.value.trim();

    if (!message) return;

    messageInput.value = '';

    sendButton.disabled = true;

    const welcomeMsg = chatContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }

    addMessage(message, 'user');

    try {
        await queryScholarVisualizations(message);

    } catch (error) {
        console.error('Error:', error);
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
    } finally {
        sendButton.disabled = false;
        messageInput.focus();
    }
}

async function queryScholarVisualizations(scholarName) {
    try {
        const [networkData, topicData, venueData] = await Promise.all([
            fetchCollaborationNetwork(scholarName),
            fetchTopicEvolution(scholarName),
            fetchVenueStats(scholarName)
        ]);

        if (networkData.error || topicData.error || venueData.error) {
            addMessage('This scholar is not currently in our database. Please try another professor.', 'assistant');
            return;
        }

        const container = createCombinedContainer();

        renderCollaborationNetwork(container.querySelector('#networkChart'), networkData.data);
        renderVenuePie(container.querySelector('#venueChartPie'), venueData.data);

        const analysisPromise = analyzeScholarData(scholarName, networkData.data, topicData.data, venueData.data, container);


        setTimeout(() => {
            const row2Container = container.querySelector('[data-delay="1000"]');
            row2Container.style.display = 'grid';
            row2Container.style.animation = 'fadeIn 0.5s ease-in';
            renderTopicEvolution(container.querySelector('#topicChart'), topicData.data);
            renderVenueBar(container.querySelector('#venueChartBar'), venueData.data);
        }, 1000);

        await analysisPromise;

    } catch (error) {
        console.error('Visualization error:', error);
        addMessage('Failed to load data. Please try again.', 'assistant');
    }
}

async function fetchCollaborationNetwork(scholarName) {
    const response = await fetch('/api/visuals/collaboration-network', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scholarName })
    });
    return await response.json();
}

async function fetchTopicEvolution(scholarName) {
    const response = await fetch('/api/visuals/topic-evolution', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scholarName })
    });
    return await response.json();
}

async function fetchVenueStats(scholarName) {
    const response = await fetch('/api/visuals/venue-stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: scholarName })
    });
    return await response.json();
}

async function analyzeScholarData(scholarName, networkData, topicData, venueData, container) {
    const analysisContent = container.querySelector('.analysis-content');

    analysisContent.textContent = '';

    let markdownContent = '';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scholar_name: scholarName,
                network_data: networkData,
                topic_data: topicData,
                venue_data: venueData
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));

                    if (data.content) {
                        const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;

                        markdownContent += data.content;

                        analysisContent.innerHTML = marked.parse(markdownContent);

                        if (isNearBottom) {
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } else if (data.done) {
                        return true;
                    } else if (data.error) {
                        analysisContent.textContent = 'Analysis failed: ' + data.error;
                        return false;
                    }
                }
            }
        }

        return true;

    } catch (error) {
        console.error('Analysis error:', error);
        analysisContent.textContent = 'Analysis failed. Please try again.';
        return false;
    }
}

function createCombinedContainer() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant full-width';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    const avatarImg = document.createElement('img');
    avatarImg.src = 'figure/web_logo/student-svgrepo-com.svg';
    avatarImg.alt = 'assistant';
    avatarDiv.appendChild(avatarImg);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content wide';

    const combinedHTML = `
        <div class="chart-row-2cols" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div class="chart-container">
                <div class="chart-title">Collaboration Network</div>
                <div id="networkChart" class="chart-wrapper"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Conference vs Journal Distribution</div>
                <div id="venueChartPie" class="chart-wrapper"></div>
            </div>
        </div>
        <div class="chart-row-2cols" style="display: none; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;" data-delay="1000">
            <div class="chart-container">
                <div class="chart-title">Research Topics Evolution</div>
                <div id="topicChart" class="chart-wrapper"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Top 10 Publication Venues</div>
                <div id="venueChartBar" class="chart-wrapper"></div>
            </div>
        </div>
        <div class="analysis-section">
            <h3>📊 Scholar Compass Analysis</h3>
            <div class="analysis-content">
                <div class="loading-chart">Analyzing research profile...</div>
            </div>
        </div>
    `;

    contentDiv.innerHTML = combinedHTML;
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return contentDiv;
}

function renderCollaborationNetwork(container, data) {
    const chart = echarts.init(container);

    const option = {
        tooltip: {
            formatter: function(params) {
                if (params.dataType === 'node') {
                    return `${params.data.name}<br/>Collaborations: ${params.data.value || 0}`;
                } else if (params.dataType === 'edge') {
                    return `Collaborations: ${params.data.value}`;
                }
            }
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: data.nodes,
            edges: data.edges,
            roam: true,
            label: {
                show: true,
                position: 'right',
                formatter: '{b}'
            },
            labelLayout: {
                hideOverlap: true
            },
            force: {
                repulsion: 500,
                edgeLength: 100
            },
            categories: [
                { name: 'Center Scholar', itemStyle: { color: '#667eea' } },
                { name: 'Collaborator', itemStyle: { color: '#764ba2' } }
            ]
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderTopicEvolution(container, data) {
    const chart = echarts.init(container);


    const topics = [...new Set(data.map(d => d.topic))];
    const years = [...new Set(data.map(d => d.year))].sort();

    const series = topics.slice(0, 10).map(topic => ({
        name: topic,
        type: 'line',
        stack: 'total',
        areaStyle: {},
        emphasis: { focus: 'series' },
        data: years.map(year => {
            const item = data.find(d => d.year === year && d.topic === topic);
            return item ? item.count : 0;
        })
    }));

    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            data: topics.slice(0, 10),
            type: 'scroll',
            bottom: 0
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: years
        },
        yAxis: {
            type: 'value'
        },
        series: series
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderVenueBar(container, data) {
    const chart = echarts.init(container);

    const topVenues = data.top_venues.slice(0, 10);

    const cleanVenueName = (name) => {
        if (!name) return '';
        return name.replace(/[\?�\ufffd\x00-\x1f\x7f-\x9f]/g, '').trim();
    };

    const truncateVenueName = (name) => {
        const cleaned = cleanVenueName(name);
        return cleaned.length > 20 ? cleaned.substring(0, 20) + '...' : cleaned;
    };

    const reversedVenues = topVenues.reverse();
    const barData = reversedVenues.map((v, index) => ({
        value: v.count,
        fullName: cleanVenueName(v.venue)
    }));

    const option = {
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                const fullVenueName = params.data.fullName;
                const count = params.value;
                return `<strong>${fullVenueName}</strong><br/>Publications: ${count}`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'value'
        },
        yAxis: {
            type: 'category',
            data: reversedVenues.map(v => truncateVenueName(v.venue))
        },
        series: [{
            name: 'Publications',
            type: 'bar',
            data: barData,
            itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: '#667eea' },
                    { offset: 1, color: '#764ba2' }
                ])
            }
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderVenuePie(container, data) {
    const chart = echarts.init(container);

    const distribution = data.distribution || [];
    const pieData = distribution.map(d => ({
        name: d.type === 'conference' ? 'Conference Papers' :
              d.type === 'journal' ? 'Journal Papers' :
              d.type.charAt(0).toUpperCase() + d.type.slice(1),
        value: d.count
    }));

    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'horizontal',
            bottom: '0%'
        },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                formatter: '{b}: {d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            data: pieData,
            color: ['#667eea', '#f687b3', '#764ba2', '#48bb78']
        }]
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function renderVenueLine(container, data) {
    const chart = echarts.init(container);

    const trends = data.trends || [];

    const venues = [...new Set(trends.map(t => t.venue))].slice(0, 5);
    const years = [...new Set(trends.map(t => t.year))].sort();


    const series = venues.map(venue => ({
        name: venue,
        type: 'line',
        smooth: true,
        data: years.map(year => {
            const item = trends.find(t => t.venue === venue && t.year === year);
            return item ? item.count : 0;
        })
    }));

    const option = {
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: venues,
            bottom: '0%',
            type: 'scroll'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: years,
            name: 'Year'
        },
        yAxis: {
            type: 'value',
            name: 'Publications'
        },
        series: series,
        color: ['#667eea', '#764ba2', '#f687b3', '#48bb78', '#ed8936']
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';

    const avatarImg = document.createElement('img');
    avatarImg.src = sender === 'user' ? 'figure/web_logo/user-svgrepo-com.svg' : 'figure/web_logo/student-svgrepo-com.svg';
    avatarImg.alt = sender;

    avatarDiv.appendChild(avatarImg);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatContainer.appendChild(messageDiv);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    return contentDiv;
}

function showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';

    const avatarImg = document.createElement('img');
    avatarImg.src = 'figure/web_logo/student-svgrepo-com.svg';
    avatarImg.alt = 'assistant';

    avatarDiv.appendChild(avatarImg);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';

    contentDiv.appendChild(typingDiv);

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatContainer.appendChild(messageDiv);

    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv;
}
