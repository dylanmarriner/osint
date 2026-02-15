<template>
  <div class="investigation-wizard">
    <div class="wizard-header">
      <h1>Investigation Wizard</h1>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
      </div>
      <span class="progress-text">Step {{ currentStep }} of {{ totalSteps }}</span>
    </div>

    <div class="wizard-container">
      <!-- Step 1: Entity Selection -->
      <div v-if="currentStep === 1" class="wizard-step">
        <h2>Who are you investigating?</h2>
        <div class="step-content">
          <div class="entity-type-selector">
            <button
              v-for="type in entityTypes"
              :key="type"
              :class="['entity-btn', { active: selectedEntityType === type }]"
              @click="selectedEntityType = type"
            >
              {{ type }}
            </button>
          </div>

          <div class="search-form">
            <label>Search for {{ selectedEntityType.toLowerCase() }}:</label>
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="`Enter ${selectedEntityType.toLowerCase()} name, email, username, etc.`"
              @keyup.enter="searchEntity"
            />
            <button class="search-btn" @click="searchEntity">Search</button>
          </div>

          <div v-if="searchResults.length > 0" class="search-results">
            <h3>Search Results:</h3>
            <div v-for="result in searchResults" :key="result.id" class="result-item">
              <input
                type="radio"
                :value="result.id"
                v-model="selectedEntity"
                :id="`result-${result.id}`"
              />
              <label :for="`result-${result.id}`">
                <div class="result-name">{{ result.name }}</div>
                <div class="result-details">{{ result.details }}</div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: Data Source Selection -->
      <div v-else-if="currentStep === 2" class="wizard-step">
        <h2>Which data sources to query?</h2>
        <div class="step-content">
          <p class="step-description">
            Select the data sources you want to search. More sources = more comprehensive results.
          </p>

          <div class="data-sources">
            <div v-for="category in dataSourceCategories" :key="category.name" class="source-category">
              <h3>{{ category.name }}</h3>
              <div class="source-list">
                <label v-for="source in category.sources" :key="source.id" class="source-item">
                  <input
                    type="checkbox"
                    v-model="selectedSources"
                    :value="source.id"
                  />
                  <span class="source-name">{{ source.name }}</span>
                  <span class="source-info">
                    <span class="confidence">{{ source.confidence }}%</span>
                    <span class="rate-limit">{{ source.rateLimit }} req/hr</span>
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div class="source-summary">
            <strong>{{ selectedSources.length }} source(s) selected</strong>
            <span v-if="estimatedTime" class="estimated-time">
              Estimated time: {{ estimatedTime }}
            </span>
          </div>
        </div>
      </div>

      <!-- Step 3: Analysis Options -->
      <div v-else-if="currentStep === 3" class="wizard-step">
        <h2>What analysis to perform?</h2>
        <div class="step-content">
          <div class="analysis-options">
            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.timeline" />
              <span class="option-title">Timeline Construction</span>
              <span class="option-description">
                Reconstruct chronological history from available data
              </span>
            </label>

            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.networkGraph" />
              <span class="option-title">Network Graph</span>
              <span class="option-description">
                Map relationships and connections between entities
              </span>
            </label>

            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.riskAssessment" />
              <span class="option-title">Risk Assessment</span>
              <span class="option-description">
                Analyze privacy exposure, security risks, and identity theft potential
              </span>
            </label>

            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.behavioralAnalysis" />
              <span class="option-title">Behavioral Analysis</span>
              <span class="option-description">
                Detect patterns, anomalies, and behavioral insights
              </span>
            </label>

            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.predictiveInsights" />
              <span class="option-title">Predictive Insights</span>
              <span class="option-description">
                Forecast likely locations, career paths, and network growth
              </span>
            </label>

            <label class="option-item">
              <input type="checkbox" v-model="analysisOptions.trendAnalysis" />
              <span class="option-title">Trend Analysis</span>
              <span class="option-description">
                Track sentiment evolution, topic trends, and growth patterns
              </span>
            </label>
          </div>
        </div>
      </div>

      <!-- Step 4: Report Options -->
      <div v-else-if="currentStep === 4" class="wizard-step">
        <h2>Report generation options</h2>
        <div class="step-content">
          <div class="report-options">
            <div class="option-group">
              <h3>Report Format</h3>
              <label v-for="format in reportFormats" :key="format" class="radio-item">
                <input type="radio" v-model="reportFormat" :value="format" />
                {{ format }}
              </label>
            </div>

            <div class="option-group">
              <h3>Report Contents</h3>
              <label v-for="section in reportSections" :key="section" class="checkbox-item">
                <input type="checkbox" v-model="reportContents" :value="section" />
                {{ section }}
              </label>
            </div>

            <div class="option-group">
              <h3>Privacy & Security</h3>
              <label class="checkbox-item">
                <input type="checkbox" v-model="reportOptions.encrypt" />
                Encrypt report (password-protected PDF)
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="reportOptions.anonymize" />
                Anonymize sensitive data
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="reportOptions.watermark" />
                Add watermark to prevent copying
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 5: Review -->
      <div v-else-if="currentStep === 5" class="wizard-step">
        <h2>Review and confirm</h2>
        <div class="step-content">
          <div class="review-section">
            <h3>Entity</h3>
            <div class="review-item">
              <span class="label">Type:</span>
              <span class="value">{{ selectedEntityType }}</span>
            </div>
            <div class="review-item">
              <span class="label">Target:</span>
              <span class="value">{{ selectedEntity }}</span>
            </div>
          </div>

          <div class="review-section">
            <h3>Data Sources ({{ selectedSources.length }})</h3>
            <div class="review-item">
              <span class="value">
                {{ getSourceNames().join(', ') }}
              </span>
            </div>
          </div>

          <div class="review-section">
            <h3>Analysis Types</h3>
            <div class="review-item">
              <ul>
                <li v-for="(enabled, key) in analysisOptions" :key="key" v-if="enabled">
                  {{ formatAnalysisName(key) }}
                </li>
              </ul>
            </div>
          </div>

          <div class="review-section">
            <h3>Report Settings</h3>
            <div class="review-item">
              <span class="label">Format:</span>
              <span class="value">{{ reportFormat }}</span>
            </div>
            <div class="review-item">
              <span class="label">Encryption:</span>
              <span class="value">{{ reportOptions.encrypt ? 'Yes' : 'No' }}</span>
            </div>
          </div>

          <div class="terms-acceptance">
            <label>
              <input type="checkbox" v-model="acceptedTerms" />
              I acknowledge that I have lawful authorization to investigate this entity
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Buttons -->
    <div class="wizard-footer">
      <button
        class="btn-previous"
        @click="previousStep"
        :disabled="currentStep === 1"
      >
        ← Previous
      </button>

      <button
        v-if="currentStep < totalSteps"
        class="btn-next"
        @click="nextStep"
        :disabled="!isStepValid"
      >
        Next →
      </button>

      <button
        v-else
        class="btn-start"
        @click="startInvestigation"
        :disabled="!acceptedTerms"
      >
        Start Investigation
      </button>

      <button class="btn-cancel" @click="cancelWizard">Cancel</button>
    </div>

    <!-- Results Preview -->
    <div v-if="investigationStarted" class="results-preview">
      <h3>Investigation in progress...</h3>
      <div class="progress-indicator">
        <div class="spinner"></div>
        <p>{{ progressMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'InvestigationWizard',
  data() {
    return {
      currentStep: 1,
      totalSteps: 5,
      
      entityTypes: ['Person', 'Company', 'Domain', 'Email', 'Phone'],
      selectedEntityType: 'Person',
      searchQuery: '',
      searchResults: [],
      selectedEntity: null,
      
      dataSourceCategories: [
        {
          name: 'Breach & Credentials',
          sources: [
            { id: 'hibp', name: 'Have I Been Pwned', confidence: 95, rateLimit: 1500 },
            { id: 'dehashed', name: 'Dehashed', confidence: 90, rateLimit: 600 },
            { id: 'leakcheck', name: 'LeakCheck', confidence: 85, rateLimit: 300 }
          ]
        },
        {
          name: 'Advanced Search',
          sources: [
            { id: 'shodan', name: 'Shodan', confidence: 85, rateLimit: 60 },
            { id: 'censys', name: 'Censys', confidence: 90, rateLimit: 120 },
            { id: 'greynoise', name: 'GreyNoise', confidence: 95, rateLimit: 150 }
          ]
        },
        {
          name: 'Public Records',
          sources: [
            { id: 'sec_edgar', name: 'SEC EDGAR', confidence: 98, rateLimit: -1 },
            { id: 'opensource', name: 'OpenCorporates', confidence: 90, rateLimit: 500 },
            { id: 'uspto', name: 'USPTO', confidence: 95, rateLimit: 2000 }
          ]
        },
        {
          name: 'Social & Funding',
          sources: [
            { id: 'crunchbase', name: 'Crunchbase', confidence: 85, rateLimit: 300 },
            { id: 'linkedin', name: 'LinkedIn Jobs', confidence: 75, rateLimit: 100 }
          ]
        }
      ],
      selectedSources: ['hibp', 'censys', 'sec_edgar'],
      
      analysisOptions: {
        timeline: true,
        networkGraph: true,
        riskAssessment: true,
        behavioralAnalysis: false,
        predictiveInsights: false,
        trendAnalysis: false
      },
      
      reportFormat: 'PDF',
      reportFormats: ['PDF', 'HTML', 'JSON', 'CSV'],
      reportSections: ['Executive Summary', 'Timeline', 'Network Graph', 'Risk Assessment', 'Recommendations'],
      reportContents: ['Executive Summary', 'Risk Assessment'],
      reportOptions: {
        encrypt: false,
        anonymize: false,
        watermark: false
      },
      
      acceptedTerms: false,
      investigationStarted: false,
      progressMessage: 'Initializing investigation...'
    };
  },

  computed: {
    progressPercentage() {
      return ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
    },

    isStepValid() {
      switch (this.currentStep) {
        case 1:
          return this.selectedEntity !== null;
        case 2:
          return this.selectedSources.length > 0;
        case 3:
          return Object.values(this.analysisOptions).some(v => v);
        case 4:
          return true;
        case 5:
          return this.acceptedTerms;
        default:
          return false;
      }
    },

    estimatedTime() {
      if (this.selectedSources.length === 0) return null;
      const avgTimePerSource = 5; // seconds
      const totalSeconds = this.selectedSources.length * avgTimePerSource;
      
      if (totalSeconds < 60) return `${totalSeconds}s`;
      if (totalSeconds < 3600) return `${Math.ceil(totalSeconds / 60)}m`;
      return `${Math.ceil(totalSeconds / 3600)}h`;
    }
  },

  methods: {
    async searchEntity() {
      // Perform real search through OSINT framework
      if (!this.searchQuery.trim()) {
        this.searchResults = [];
        return;
      }
      
      try {
        // Call actual API to search for entity
        const response = await fetch('/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            query: this.searchQuery,
            entityType: this.selectedEntityType
          })
        });
        
        if (!response.ok) {
          throw new Error(`Search failed: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Transform API results into UI format
        this.searchResults = (data.results || []).map(result => ({
          id: result.id || result.value,
          name: result.value || result.name,
          type: result.entity_type || this.selectedEntityType,
          details: `${this.selectedEntityType} - Found in ${result.source_count || 1} data sources`,
          confidence: result.confidence || 0.8,
          metadata: result.metadata || {}
        }));
        
        // If no results, show no-results message
        if (this.searchResults.length === 0) {
          this.searchResults = [{
            id: 'no-results',
            name: 'No results found',
            type: 'info',
            details: `No ${this.selectedEntityType.toLowerCase()} matching "${this.searchQuery}" found`,
            confidence: 0
          }];
        }
      } catch (error) {
        console.error('Search error:', error);
        this.searchResults = [{
          id: 'error',
          name: 'Search Error',
          type: 'error',
          details: `Failed to search: ${error.message}`,
          confidence: 0
        }];
      }
    },

    nextStep() {
      if (this.isStepValid && this.currentStep < this.totalSteps) {
        this.currentStep++;
      }
    },

    previousStep() {
      if (this.currentStep > 1) {
        this.currentStep--;
      }
    },

    getSourceNames() {
      const names = [];
      for (const category of this.dataSourceCategories) {
        for (const source of category.sources) {
          if (this.selectedSources.includes(source.id)) {
            names.push(source.name);
          }
        }
      }
      return names;
    },

    formatAnalysisName(key) {
      return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
    },

    startInvestigation() {
      this.investigationStarted = true;
      this.$emit('investigation-started', {
        entityType: this.selectedEntityType,
        entityId: this.selectedEntity,
        sources: this.selectedSources,
        analysis: this.analysisOptions,
        reportOptions: {
          format: this.reportFormat,
          contents: this.reportContents,
          ...this.reportOptions
        }
      });
    },

    cancelWizard() {
      this.$emit('cancelled');
    }
  }
};
</script>

<style scoped>
.investigation-wizard {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.wizard-header {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 30px;
}

.wizard-header h1 {
  margin-top: 0;
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #ddd;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(to right, #4285F4, #34A853);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 12px;
  color: #999;
}

.wizard-container {
  background: white;
  border-radius: 8px;
  padding: 30px;
  margin-bottom: 20px;
  min-height: 400px;
}

.wizard-step h2 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
}

.step-content {
  margin-bottom: 20px;
}

.entity-type-selector {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.entity-btn {
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s ease;
}

.entity-btn:hover {
  border-color: #007bff;
  background: #f0f7ff;
}

.entity-btn.active {
  border-color: #007bff;
  background: #007bff;
  color: white;
}

.search-form {
  margin-bottom: 20px;
}

.search-form label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
}

.search-form input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 14px;
}

.search-btn {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.search-btn:hover {
  background: #0056b3;
}

.search-results {
  margin-top: 20px;
}

.search-results h3 {
  margin-bottom: 10px;
}

.result-item {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.result-item:hover {
  background: #f9f9f9;
}

.result-item input[type="radio"] {
  margin-right: 12px;
  margin-top: 2px;
}

.result-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.result-details {
  font-size: 12px;
  color: #999;
}

.step-description {
  color: #666;
  margin-bottom: 15px;
}

.data-sources {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.source-category h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.source-item:hover {
  background: #f0f7ff;
}

.source-item input[type="checkbox"] {
  margin: 0;
}

.source-name {
  font-weight: bold;
  flex: 1;
}

.source-info {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #999;
}

.source-summary {
  margin-top: 20px;
  padding: 12px;
  background: #f0f7ff;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.estimated-time {
  color: #666;
  font-size: 12px;
}

.analysis-options {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.option-item:hover {
  background: #f9f9f9;
}

.option-item input[type="checkbox"] {
  margin-top: 2px;
}

.option-title {
  display: block;
  font-weight: bold;
  margin-bottom: 4px;
}

.option-description {
  display: block;
  font-size: 12px;
  color: #666;
}

.report-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.option-group h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
}

.radio-item,
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.radio-item input[type="radio"],
.checkbox-item input[type="checkbox"] {
  margin: 0;
}

.review-section {
  margin-bottom: 20px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.review-section h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 14px;
}

.review-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #eee;
}

.review-item:last-child {
  border-bottom: none;
}

.review-item .label {
  font-weight: bold;
  color: #666;
}

.review-item .value {
  color: #333;
}

.review-item ul {
  margin: 0;
  padding-left: 20px;
}

.review-item li {
  margin-bottom: 4px;
}

.terms-acceptance {
  margin-top: 20px;
  padding: 15px;
  background: #fff3cd;
  border-radius: 4px;
}

.terms-acceptance label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
}

.terms-acceptance input[type="checkbox"] {
  margin-top: 2px;
}

.wizard-footer {
  display: flex;
  gap: 10px;
  justify-content: center;
  background: white;
  padding: 20px;
  border-radius: 8px;
}

button {
  padding: 10px 20px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s ease;
}

.btn-previous:hover:not(:disabled),
.btn-cancel:hover {
  background: #f0f0f0;
}

.btn-next,
.btn-start {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.btn-next:hover:not(:disabled),
.btn-start:hover:not(:disabled) {
  background: #0056b3;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.results-preview {
  background: white;
  padding: 30px;
  border-radius: 8px;
  text-align: center;
}

.progress-indicator {
  margin-top: 20px;
}

.spinner {
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .entity-type-selector {
    grid-template-columns: repeat(2, 1fr);
  }

  .data-sources {
    grid-template-columns: 1fr;
  }

  .report-options {
    grid-template-columns: 1fr;
  }

  .wizard-footer {
    flex-wrap: wrap;
  }
}
</style>
