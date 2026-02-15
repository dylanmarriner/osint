<template>
  <div class="risk-dashboard">
    <div class="dashboard-header">
      <h1>Risk Assessment Dashboard</h1>
      <div class="refresh-controls">
        <button @click="refreshAnalysis">Refresh Analysis</button>
        <span v-if="lastUpdated" class="last-updated">
          Last updated: {{ formatTime(lastUpdated) }}
        </span>
      </div>
    </div>

    <div class="overview-metrics">
      <div class="metric-card overall-risk">
        <div class="metric-value">{{ overallRiskScore }}</div>
        <div class="metric-label">Overall Risk Score</div>
        <div :class="['metric-level', riskLevel]">{{ riskLevel }}</div>
        <div class="metric-description">
          <small>{{ riskDescription }}</small>
        </div>
      </div>

      <div class="metric-card privacy-score">
        <div class="metric-value">{{ privacyScore }}</div>
        <div class="metric-label">Privacy Exposure</div>
        <div class="metric-bar">
          <div class="bar-fill" :style="{ width: privacyScore + '%' }"></div>
        </div>
      </div>

      <div class="metric-card security-score">
        <div class="metric-value">{{ securityScore }}</div>
        <div class="metric-label">Security Risk</div>
        <div class="metric-bar">
          <div class="bar-fill" :style="{ width: securityScore + '%' }"></div>
        </div>
      </div>

      <div class="metric-card identity-score">
        <div class="metric-value">{{ identityTheftRisk }}</div>
        <div class="metric-label">Identity Theft Risk</div>
        <div class="metric-bar">
          <div class="bar-fill" :style="{ width: identityTheftRisk + '%' }"></div>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="left-panel">
        <div class="risk-breakdown">
          <h3>Risk Factor Breakdown</h3>
          <div class="pie-chart">
            <svg width="200" height="200" viewBox="0 0 200 200">
              <circle cx="100" cy="100" r="90" fill="none" stroke="#f0f0f0" stroke-width="30"></circle>
              <circle
                v-for="(segment, index) in riskSegments"
                :key="index"
                cx="100"
                cy="100"
                r="90"
                fill="none"
                :stroke="segment.color"
                stroke-width="30"
                :stroke-dasharray="segment.circumference"
                :stroke-dashoffset="segment.offset"
                :transform="`rotate(${segment.rotation} 100 100)`"
              ></circle>
            </svg>
          </div>
          <div class="chart-legend">
            <div v-for="factor in riskFactors" :key="factor.name" class="legend-item">
              <span class="legend-color" :style="{ background: factor.color }"></span>
              <span class="legend-label">{{ factor.name }}: {{ factor.percentage }}%</span>
            </div>
          </div>
        </div>

        <div class="vulnerabilities-list">
          <h3>Critical Vulnerabilities</h3>
          <div v-if="vulnerabilities.length === 0" class="empty-state">
            <p>No critical vulnerabilities detected</p>
          </div>
          <div v-for="vuln in vulnerabilities" :key="vuln.id" :class="['vulnerability-item', vuln.severity]">
            <div class="vuln-header">
              <span class="vuln-title">{{ vuln.title }}</span>
              <span :class="['vuln-severity', vuln.severity]">{{ vuln.severity }}</span>
            </div>
            <p class="vuln-description">{{ vuln.description }}</p>
            <div class="vuln-footer">
              <span class="affected-count">Affects: {{ vuln.affected_count }} account(s)</span>
              <span class="remediation-effort">Fix effort: {{ vuln.remediation_effort }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="breach-timeline">
          <h3>Data Breach Timeline</h3>
          <div class="chart-container">
            <svg width="100%" height="300" viewBox="0 0 400 300">
              <!-- Chart would render here -->
              <text x="200" y="150" text-anchor="middle" fill="#999">
                Breach timeline chart would render here
              </text>
            </svg>
          </div>
        </div>

        <div class="recommendations">
          <h3>Top Recommendations</h3>
          <div v-if="recommendations.length === 0" class="empty-state">
            <p>All recommended actions completed</p>
          </div>
          <div v-for="(rec, index) in recommendations" :key="index" class="recommendation-card">
            <div class="rec-header">
              <span class="rec-priority" :class="rec.priority.toLowerCase()">
                {{ rec.priority }}
              </span>
              <span class="rec-impact">Impact: {{ rec.impact_reduction }}%</span>
            </div>
            <p class="rec-action">{{ rec.action }}</p>
            <p class="rec-description">{{ rec.description }}</p>
            <div class="rec-effort">
              Effort: <strong>{{ rec.effort }}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="risk-trend">
      <h3>Risk Score Trend (Last 30 Days)</h3>
      <div class="trend-chart">
        <svg width="100%" height="200" viewBox="0 0 400 200">
          <!-- Trend line chart would render here -->
          <text x="200" y="100" text-anchor="middle" fill="#999">
            Risk trend chart would render here
          </text>
        </svg>
      </div>
    </div>

    <div class="peer-comparison">
      <h3>Comparative Risk Analysis</h3>
      <div class="comparison-table">
        <div class="table-header">
          <div class="col">Metric</div>
          <div class="col">This Person</div>
          <div class="col">Peer Average</div>
          <div class="col">Status</div>
        </div>
        <div v-for="(item, index) in peerComparison" :key="index" class="table-row">
          <div class="col">{{ item.metric }}</div>
          <div class="col">{{ item.personal }}</div>
          <div class="col">{{ item.average }}</div>
          <div :class="['col', 'status', item.status.toLowerCase()]">
            {{ item.status }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RiskDashboard',
  props: {
    riskAssessment: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      lastUpdated: null,
      overallRiskScore: 65,
      privacyScore: 72,
      securityScore: 58,
      identityTheftRisk: 55,
      riskLevel: 'HIGH',
      riskDescription: 'Your information is exposed in multiple data breaches',
      
      riskFactors: [
        { name: 'Privacy Exposure', percentage: 35, color: '#FF6B6B' },
        { name: 'Security Risk', percentage: 30, color: '#FFA500' },
        { name: 'Identity Theft', percentage: 20, color: '#FFD93D' },
        { name: 'Network Risk', percentage: 15, color: '#6BCFE4' }
      ],

      vulnerabilities: [
        {
          id: 1,
          title: 'Email Found in Breach Database',
          description: 'Your email was exposed in the Adobe breach (2013). Recommend changing password.',
          severity: 'CRITICAL',
          affected_count: 1,
          remediation_effort: 'LOW'
        },
        {
          id: 2,
          title: 'Weak Password Pattern',
          description: 'Multiple accounts use similar passwords. Unique passwords reduce risk.',
          severity: 'HIGH',
          affected_count: 3,
          remediation_effort: 'MEDIUM'
        },
        {
          id: 3,
          title: 'Missing 2FA Protection',
          description: 'Email and financial accounts lack 2FA. Enabling 2FA significantly improves security.',
          severity: 'HIGH',
          affected_count: 2,
          remediation_effort: 'MEDIUM'
        }
      ],

      recommendations: [
        {
          priority: 'CRITICAL',
          action: 'Change password for all Adobe-affected accounts',
          description: 'Your email was exposed in the 2013 Adobe breach affecting 150M users.',
          impact_reduction: 25,
          effort: 'LOW'
        },
        {
          priority: 'HIGH',
          action: 'Enable two-factor authentication',
          description: 'Add 2FA to your email and financial accounts to prevent unauthorized access.',
          impact_reduction: 35,
          effort: 'MEDIUM'
        },
        {
          priority: 'HIGH',
          action: 'Use unique passwords',
          description: 'Update accounts using similar passwords with unique, strong passwords.',
          impact_reduction: 20,
          effort: 'MEDIUM'
        },
        {
          priority: 'MEDIUM',
          action: 'Monitor credit reports',
          description: 'Sign up for free credit monitoring given the PII exposure.',
          impact_reduction: 15,
          effort: 'LOW'
        },
        {
          priority: 'MEDIUM',
          action: 'Review social media privacy',
          description: 'Limit visibility of personal information on social profiles.',
          impact_reduction: 10,
          effort: 'LOW'
        }
      ],

      peerComparison: [
        { metric: 'Overall Risk Score', personal: '65', average: '52', status: 'Above Average' },
        { metric: 'Breach Exposure', personal: '3 breaches', average: '1.2 breaches', status: 'Above Average' },
        { metric: 'Data Points Exposed', personal: '47', average: '28', status: 'Above Average' },
        { metric: 'Account Security', personal: '40%', average: '65%', status: 'Below Average' },
        { metric: '2FA Adoption', personal: '25%', average: '45%', status: 'Below Average' }
      ]
    };
  },

  computed: {
    riskSegments() {
      const circumference = 2 * Math.PI * 90;
      let offset = 0;
      
      return this.riskFactors.map(factor => {
        const percentage = factor.percentage;
        const segmentCircumference = (percentage / 100) * circumference;
        const rotation = (offset / circumference) * 360;
        
        const segment = {
          color: factor.color,
          circumference: segmentCircumference,
          offset: circumference - offset,
          rotation: rotation
        };
        
        offset += segmentCircumference;
        return segment;
      });
    }
  },

  mounted() {
    this.lastUpdated = new Date();
    // Load risk assessment data
    this.loadRiskAssessment();
  },

  methods: {
    loadRiskAssessment() {
      // Load data from props
      if (this.riskAssessment) {
        this.overallRiskScore = Math.round(this.riskAssessment.overall_risk_score || 65);
        this.privacyScore = Math.round(this.riskAssessment.privacy_exposure_score || 72);
        this.securityScore = Math.round(this.riskAssessment.security_risk_score || 58);
        this.identityTheftRisk = Math.round(this.riskAssessment.identity_theft_risk || 55);
        
        if (this.overallRiskScore > 70) {
          this.riskLevel = 'CRITICAL';
          this.riskDescription = 'Critical security and privacy risks detected';
        } else if (this.overallRiskScore > 50) {
          this.riskLevel = 'HIGH';
          this.riskDescription = 'Multiple high-priority security issues';
        } else if (this.overallRiskScore > 30) {
          this.riskLevel = 'MEDIUM';
          this.riskDescription = 'Some areas need attention';
        } else {
          this.riskLevel = 'LOW';
          this.riskDescription = 'Good security practices in place';
        }
      }
    },

    refreshAnalysis() {
      this.lastUpdated = new Date();
      this.$emit('refresh-requested');
    },

    formatTime(date) {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
  }
};
</script>

<style scoped>
.risk-dashboard {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.refresh-controls {
  display: flex;
  gap: 15px;
  align-items: center;
}

.refresh-controls button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.refresh-controls button:hover {
  background: #0056b3;
}

.last-updated {
  font-size: 12px;
  color: #999;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.metric-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 10px;
}

.metric-label {
  font-size: 14px;
  color: #999;
  margin-bottom: 10px;
}

.metric-level {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  margin-bottom: 10px;
}

.metric-level.CRITICAL {
  background: #ffebee;
  color: #c62828;
}

.metric-level.HIGH {
  background: #fff3e0;
  color: #e65100;
}

.metric-level.MEDIUM {
  background: #fff8e1;
  color: #f57f17;
}

.metric-level.LOW {
  background: #e8f5e9;
  color: #2e7d32;
}

.metric-description {
  font-size: 12px;
  color: #666;
}

.metric-bar {
  width: 100%;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 10px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(to right, #ff6b6b, #ffa500, #6bcf7f);
  border-radius: 4px;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 30px;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.risk-breakdown,
.vulnerabilities-list,
.breach-timeline,
.recommendations {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.risk-breakdown h3,
.vulnerabilities-list h3,
.breach-timeline h3,
.recommendations h3 {
  margin-top: 0;
  margin-bottom: 15px;
}

.pie-chart {
  display: flex;
  justify-content: center;
  margin-bottom: 15px;
}

.chart-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #999;
}

.vulnerability-item {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 10px;
  border-left: 4px solid #ccc;
}

.vulnerability-item.CRITICAL {
  border-left-color: #c62828;
  background: #ffebee;
}

.vulnerability-item.HIGH {
  border-left-color: #e65100;
  background: #fff3e0;
}

.vulnerability-item.MEDIUM {
  border-left-color: #f57f17;
  background: #fff8e1;
}

.vuln-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.vuln-title {
  font-weight: bold;
  font-size: 13px;
}

.vuln-severity {
  font-size: 11px;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 3px;
}

.vuln-severity.CRITICAL {
  background: #c62828;
  color: white;
}

.vuln-severity.HIGH {
  background: #e65100;
  color: white;
}

.vuln-severity.MEDIUM {
  background: #f57f17;
  color: white;
}

.vuln-description {
  font-size: 12px;
  color: #666;
  margin: 8px 0;
}

.vuln-footer {
  display: flex;
  gap: 15px;
  font-size: 11px;
  color: #999;
}

.chart-container {
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.recommendation-card {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 10px;
  background: #f9f9f9;
}

.rec-header {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.rec-priority {
  display: inline-block;
  font-size: 11px;
  font-weight: bold;
  padding: 4px 8px;
  border-radius: 3px;
  min-width: 60px;
  text-align: center;
}

.rec-priority.critical {
  background: #c62828;
  color: white;
}

.rec-priority.high {
  background: #e65100;
  color: white;
}

.rec-priority.medium {
  background: #f57f17;
  color: white;
}

.rec-impact {
  font-size: 11px;
  color: #999;
}

.rec-action {
  font-weight: bold;
  font-size: 13px;
  margin: 0 0 5px 0;
}

.rec-description {
  font-size: 12px;
  color: #666;
  margin: 0 0 5px 0;
}

.rec-effort {
  font-size: 11px;
  color: #999;
}

.risk-trend,
.peer-comparison {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.risk-trend h3,
.peer-comparison h3 {
  margin-top: 0;
  margin-bottom: 15px;
}

.trend-chart {
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.comparison-table {
  width: 100%;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 15px;
  padding: 12px;
  border-bottom: 1px solid #ddd;
}

.table-header {
  background: #f5f5f5;
  font-weight: bold;
  font-size: 13px;
}

.table-row .col {
  font-size: 13px;
}

.col.status {
  font-weight: bold;
}

.col.status.above {
  color: #e65100;
}

.col.status.below {
  color: #2e7d32;
}

.col.status.average {
  color: #999;
}
</style>
