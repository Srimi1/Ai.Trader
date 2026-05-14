# Agency Agents — Reference Sheet

All agents from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
installed to `~/.claude/agents/`. Use `@<name>` in any Claude Code conversation.

Short aliases created for all key agents. Full original names also work.

---

## How to Use

```
@analyst analyse DXCM balance sheet
@investor run Munger Invert on TDG
@reviewer review this PR
@db optimise this query
```

---

## Finance (Most Relevant for AI.Trader)

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@analyst` | `finance-financial-analyst` | Morgan — Financial Analyst | Financial modeling, forecasting, scenario analysis, cash flow |
| `@investor` | `finance-investment-researcher` | Quinn — Investment Researcher | Due diligence, portfolio analysis, Lynch Pitch / Munger Invert style |
| `@fpa` | `finance-fpa-analyst` | FP&A Analyst | Budgeting, variance analysis, guidance vs reality |
| `@tax` | `finance-tax-strategist` | Tax Strategist | Tax optimization, multi-jurisdictional compliance |
| `@bookkeeper` | `finance-bookkeeper-controller` | Bookkeeper & Controller | Day-to-day accounting, financial controls |
| `@tracker` | `support-finance-tracker` | Finance Tracker | Financial planning, budgeting, expenditure tracking |

---

## Engineering

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@architect` | `engineering-software-architect` | Software Architect | System design, DDD, microservices, architecture decisions |
| `@backend` | `engineering-backend-architect` | Backend Architect | Scalable backend, database architecture, API design |
| `@frontend` | `engineering-frontend-developer` | Frontend Developer | React/Vue/Angular, component libraries |
| `@senior-dev` | `engineering-senior-developer` | Senior Developer | Laravel/Livewire, advanced CS, premium implementation |
| `@ai-eng` | `engineering-ai-engineer` | AI Engineer | ML model development, deployment, inference optimization |
| `@data-eng` | `engineering-data-engineer` | Data Engineer | Data pipelines, lakehouse, ETL, Spark, dbt |
| `@db` | `engineering-database-optimizer` | Database Optimizer | Schema design, query optimization, indexing |
| `@devops` | `engineering-devops-automator` | DevOps Automator | CI/CD, infrastructure automation, Docker/K8s |
| `@security` | `engineering-security-engineer` | Security Engineer | Threat modeling, OWASP, AppSec, penetration testing |
| `@sre` | `engineering-sre` | SRE | SLOs, error budgets, observability, on-call runbooks |
| `@reviewer` | `engineering-code-reviewer` | Code Reviewer | Constructive code review, best practices, PR feedback |
| `@mobile` | `engineering-mobile-app-builder` | Mobile App Builder | iOS/Android, React Native, Flutter |
| `@git` | `engineering-git-workflow-master` | Git Workflow Master | Branching strategies, merge conflicts, rebase workflows |
| `@writer` | `engineering-technical-writer` | Technical Writer | Developer docs, API references, READMEs |
| `@incident` | `engineering-incident-response-commander` | Incident Response Commander | Production incidents, postmortems, runbooks |
| `@prototyper` | `engineering-rapid-prototyper` | Rapid Prototyper | Fast MVP/POC development |
| `@data-fix` | `engineering-ai-data-remediation-engineer` | AI Data Remediation Engineer | Self-healing data pipelines |

---

## Testing & Quality

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@api-test` | `testing-api-tester` | API Tester | API validation, performance, contract testing |
| `@perf-test` | `testing-performance-benchmarker` | Performance Benchmarker | Load testing, profiling, optimization |
| `@reality` | `testing-reality-checker` | Reality Checker | Evidence-based QA, stops hallucinated approvals |
| `@a11y` | `testing-accessibility-auditor` | Accessibility Auditor | WCAG compliance, screen reader testing |
| `@workflow-opt` | `testing-workflow-optimizer` | Workflow Optimizer | Process improvement, bottleneck analysis |

---

## Product & Project

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@pm` | `product-manager` | Product Manager | Full product lifecycle, discovery, roadmap |
| `@sprint` | `product-sprint-prioritizer` | Sprint Prioritizer | Agile sprint planning, feature backlog |
| `@trend` | `product-trend-researcher` | Trend Researcher | Market intelligence, emerging trends |
| `@pm-senior` | `project-manager-senior` | Senior Project Manager | Specs → tasks, realistic scoping |
| `@shepherd` | `project-management-project-shepherd` | Project Shepherd | Cross-functional coordination, risk tracking |

---

## Specialized

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@mcp-build` | `specialized-mcp-builder` | MCP Builder | Design and build MCP servers (pairs with /mcp creator) |
| `@cos` | `specialized-chief-of-staff` | Chief of Staff | Executive coordination, decision support |
| `@doc-gen` | `specialized-document-generator` | Document Generator | PDF/PPTX/DOCX generation |
| `@model-qa` | `specialized-model-qa` | Model QA Specialist | ML model auditing, statistical validation |
| `@workflow-arch` | `specialized-workflow-architect` | Workflow Architect | Complete workflow trees, automation mapping |
| `@orchestrator` | `agents-orchestrator` | Agents Orchestrator | Multi-agent pipeline management |

---

## Sales & Business

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@deal` | `sales-deal-strategist` | Deal Strategist | MEDDPICC qualification, competitive deals |
| `@pipeline` | `sales-pipeline-analyst` | Pipeline Analyst | Revenue ops, pipeline health, forecasting |
| `@proposal` | `sales-proposal-strategist` | Proposal Strategist | RFPs, sales proposals |
| `@coach` | `sales-coach` | Sales Coach | Rep development, pipeline reviews |
| `@outbound` | `sales-outbound-strategist` | Outbound Strategist | Signal-based prospecting, multi-channel sequences |

---

## Support & Operations

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@summary` | `support-executive-summary-generator` | Executive Summary Generator | Consultant-grade executive summaries |
| `@analytics` | `support-analytics-reporter` | Analytics Reporter | Raw data → actionable business insights |
| `@legal-check` | `support-legal-compliance-checker` | Legal Compliance Checker | Compliance review, risk flagging |
| `@support` | `support-support-responder` | Support Responder | Customer support, issue resolution |
| `@supply` | `supply-chain-strategist` | Supply Chain Strategist | Supply chain management, procurement |

---

## Design

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@ui` | `design-ui-designer` | UI Designer | Visual design systems, component libraries |
| `@ux` | `design-ux-architect` | UX Architect | UX architecture, developer-ready specs |
| `@brand` | `design-brand-guardian` | Brand Guardian | Brand identity, guidelines enforcement |

---

## Compliance & Legal

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@compliance` | `compliance-auditor` | Compliance Auditor | SOC 2, ISO 27001, HIPAA, GDPR |
| `@legal-review` | `legal-document-review` | Legal Document Review | Contracts, litigation documents |
| `@blockchain-sec` | `blockchain-security-auditor` | Blockchain Security Auditor | Smart contract auditing, Solidity security |

---

## Academic / Research

| Short Name | Original File | Agent Name | What It Does |
|-----------|---------------|-----------|--------------|
| `@historian` | `academic-historian` | Historian | Historical analysis, research |
| `@psychologist` | `academic-psychologist` | Psychologist | Behavioral patterns, cognitive analysis |

---

## All 184 Original Agent Names (Full List)

<details>
<summary>Click to expand full list</summary>

| Original Name | Category | Short Alias |
|--------------|----------|-------------|
| `academic-anthropologist` | Academic | — |
| `academic-geographer` | Academic | — |
| `academic-historian` | Academic | `@historian` |
| `academic-narratologist` | Academic | — |
| `academic-psychologist` | Academic | `@psychologist` |
| `accounts-payable-agent` | Finance | — |
| `agentic-identity-trust` | Specialized | — |
| `agents-orchestrator` | Orchestration | `@orchestrator` |
| `automation-governance-architect` | Specialized | — |
| `blender-addon-engineer` | Engineering | — |
| `blockchain-security-auditor` | Security | `@blockchain-sec` |
| `compliance-auditor` | Compliance | `@compliance` |
| `corporate-training-designer` | HR | — |
| `customer-service` | Support | — |
| `data-consolidation-agent` | Data | `@consolidate` |
| `design-brand-guardian` | Design | `@brand` |
| `design-image-prompt-engineer` | Design | — |
| `design-inclusive-visuals-specialist` | Design | — |
| `design-ui-designer` | Design | `@ui` |
| `design-ux-architect` | Design | `@ux` |
| `design-ux-researcher` | Design | — |
| `design-visual-storyteller` | Design | — |
| `design-whimsy-injector` | Design | — |
| `engineering-ai-data-remediation-engineer` | Engineering | `@data-fix` |
| `engineering-ai-engineer` | Engineering | `@ai-eng` |
| `engineering-autonomous-optimization-architect` | Engineering | — |
| `engineering-backend-architect` | Engineering | `@backend` |
| `engineering-cms-developer` | Engineering | — |
| `engineering-code-reviewer` | Engineering | `@reviewer` |
| `engineering-codebase-onboarding-engineer` | Engineering | — |
| `engineering-data-engineer` | Engineering | `@data-eng` |
| `engineering-database-optimizer` | Engineering | `@db` |
| `engineering-devops-automator` | Engineering | `@devops` |
| `engineering-email-intelligence-engineer` | Engineering | — |
| `engineering-embedded-firmware-engineer` | Engineering | — |
| `engineering-feishu-integration-developer` | Engineering | — |
| `engineering-filament-optimization-specialist` | Engineering | — |
| `engineering-frontend-developer` | Engineering | `@frontend` |
| `engineering-git-workflow-master` | Engineering | `@git` |
| `engineering-incident-response-commander` | Engineering | `@incident` |
| `engineering-minimal-change-engineer` | Engineering | — |
| `engineering-mobile-app-builder` | Engineering | `@mobile` |
| `engineering-rapid-prototyper` | Engineering | `@prototyper` |
| `engineering-security-engineer` | Engineering | `@security` |
| `engineering-senior-developer` | Engineering | `@senior-dev` |
| `engineering-software-architect` | Engineering | `@architect` |
| `engineering-solidity-smart-contract-engineer` | Engineering | — |
| `engineering-sre` | Engineering | `@sre` |
| `engineering-technical-writer` | Engineering | `@writer` |
| `engineering-threat-detection-engineer` | Engineering | — |
| `engineering-voice-ai-integration-engineer` | Engineering | — |
| `engineering-wechat-mini-program-developer` | Engineering | — |
| `finance-bookkeeper-controller` | Finance | `@bookkeeper` |
| `finance-financial-analyst` | Finance | `@analyst` |
| `finance-fpa-analyst` | Finance | `@fpa` |
| `finance-investment-researcher` | Finance | `@investor` |
| `finance-tax-strategist` | Finance | `@tax` |
| `game-audio-engineer` | Game Dev | — |
| `game-designer` | Game Dev | — |
| `godot-gameplay-scripter` | Game Dev | — |
| `godot-multiplayer-engineer` | Game Dev | — |
| `godot-shader-developer` | Game Dev | — |
| `government-digital-presales-consultant` | Specialized | — |
| `healthcare-customer-service` | Healthcare | — |
| `healthcare-marketing-compliance` | Healthcare | — |
| `hospitality-guest-services` | Hospitality | — |
| `hr-onboarding` | HR | — |
| `identity-graph-operator` | Specialized | — |
| `language-translator` | Specialized | — |
| `legal-billing-time-tracking` | Legal | — |
| `legal-client-intake` | Legal | — |
| `legal-document-review` | Legal | `@legal-review` |
| `level-designer` | Game Dev | — |
| `loan-officer-assistant` | Finance | — |
| `lsp-index-engineer` | Engineering | — |
| `macos-spatial-metal-engineer` | Engineering | — |
| `marketing-agentic-search-optimizer` | Marketing | — |
| `marketing-ai-citation-strategist` | Marketing | — |
| `marketing-app-store-optimizer` | Marketing | — |
| `marketing-content-creator` | Marketing | — |
| `marketing-growth-hacker` | Marketing | — |
| `marketing-instagram-curator` | Marketing | — |
| `marketing-linkedin-content-creator` | Marketing | — |
| `marketing-podcast-strategist` | Marketing | — |
| `marketing-reddit-community-builder` | Marketing | — |
| `marketing-seo-specialist` | Marketing | — |
| `marketing-social-media-strategist` | Marketing | — |
| `marketing-tiktok-strategist` | Marketing | — |
| `marketing-twitter-engager` | Marketing | — |
| `narrative-designer` | Game Dev | — |
| `paid-media-auditor` | Marketing | — |
| `paid-media-ppc-strategist` | Marketing | — |
| `product-behavioral-nudge-engine` | Product | — |
| `product-feedback-synthesizer` | Product | — |
| `product-manager` | Product | `@pm` |
| `product-sprint-prioritizer` | Product | `@sprint` |
| `product-trend-researcher` | Product | `@trend` |
| `project-management-experiment-tracker` | Project Mgmt | — |
| `project-management-jira-workflow-steward` | Project Mgmt | — |
| `project-management-project-shepherd` | Project Mgmt | `@shepherd` |
| `project-management-studio-operations` | Project Mgmt | — |
| `project-management-studio-producer` | Project Mgmt | — |
| `project-manager-senior` | Project Mgmt | `@pm-senior` |
| `real-estate-buyer-seller` | Specialized | — |
| `recruitment-specialist` | HR | — |
| `report-distribution-agent` | Support | — |
| `retail-customer-returns` | Retail | — |
| `roblox-avatar-creator` | Game Dev | — |
| `roblox-experience-designer` | Game Dev | — |
| `roblox-systems-scripter` | Game Dev | — |
| `sales-account-strategist` | Sales | — |
| `sales-coach` | Sales | `@coach` |
| `sales-data-extraction-agent` | Sales | — |
| `sales-deal-strategist` | Sales | `@deal` |
| `sales-discovery-coach` | Sales | — |
| `sales-engineer` | Sales | — |
| `sales-outbound-strategist` | Sales | `@outbound` |
| `sales-outreach` | Sales | — |
| `sales-pipeline-analyst` | Sales | `@pipeline` |
| `sales-proposal-strategist` | Sales | `@proposal` |
| `specialized-chief-of-staff` | Specialized | `@cos` |
| `specialized-civil-engineer` | Engineering | — |
| `specialized-cultural-intelligence-strategist` | Specialized | — |
| `specialized-developer-advocate` | Specialized | — |
| `specialized-document-generator` | Specialized | `@doc-gen` |
| `specialized-mcp-builder` | Specialized | `@mcp-build` |
| `specialized-model-qa` | Specialized | `@model-qa` |
| `specialized-salesforce-architect` | Specialized | — |
| `specialized-workflow-architect` | Specialized | `@workflow-arch` |
| `supply-chain-strategist` | Operations | `@supply` |
| `support-analytics-reporter` | Support | `@analytics` |
| `support-executive-summary-generator` | Support | `@summary` |
| `support-finance-tracker` | Finance | `@tracker` |
| `support-infrastructure-maintainer` | Engineering | — |
| `support-legal-compliance-checker` | Legal | `@legal-check` |
| `support-support-responder` | Support | `@support` |
| `testing-accessibility-auditor` | Testing | `@a11y` |
| `testing-api-tester` | Testing | `@api-test` |
| `testing-evidence-collector` | Testing | — |
| `testing-performance-benchmarker` | Testing | `@perf-test` |
| `testing-reality-checker` | Testing | `@reality` |
| `testing-test-results-analyzer` | Testing | — |
| `testing-tool-evaluator` | Testing | — |
| `testing-workflow-optimizer` | Testing | `@workflow-opt` |
| `unity-architect` | Game Dev | — |
| `unity-editor-tool-developer` | Game Dev | — |
| `unity-multiplayer-engineer` | Game Dev | — |
| `unity-shader-graph-artist` | Game Dev | — |
| `unreal-multiplayer-architect` | Game Dev | — |
| `unreal-systems-engineer` | Game Dev | — |
| `unreal-technical-artist` | Game Dev | — |
| `unreal-world-builder` | Game Dev | — |
| `visionos-spatial-engineer` | Engineering | — |
| `xr-cockpit-interaction-specialist` | XR | — |
| `xr-immersive-developer` | XR | — |
| `xr-interface-architect` | XR | — |
| `zk-steward` | Knowledge | — |

</details>

---

## Quick Reference Card (AI.Trader Most Useful)

```
FINANCE
@analyst    → Financial Analyst (Morgan) — balance sheets, cash flow, models
@investor   → Investment Researcher (Quinn) — due diligence, Lynch/Munger analysis
@fpa        → FP&A Analyst — earnings vs guidance, variance
@tax        → Tax Strategist — tax optimization
@tracker    → Finance Tracker — budgeting, expenditure

ENGINEERING
@architect  → Software Architect — system design, ADRs
@backend    → Backend Architect — API, DB design
@reviewer   → Code Reviewer — PR review, best practices
@data-eng   → Data Engineer — pipelines, ETL
@db         → Database Optimizer — schema, query optimization
@devops     → DevOps Automator — CI/CD, infrastructure
@security   → Security Engineer — threat modeling, OWASP
@sre        → Site Reliability Engineer — SLOs, observability

TESTING
@api-test   → API Tester — endpoint validation
@reality    → Reality Checker — evidence-based QA (stops hallucinations)
@perf-test  → Performance Benchmarker — load testing

SPECIALIZED
@mcp-build  → MCP Builder — pairs with /mcp creator skill
@orchestrator → Agents Orchestrator — multi-agent pipelines
@model-qa   → Model QA — ML model auditing
@summary    → Executive Summary Generator

PRODUCT
@pm         → Product Manager — roadmap, discovery
@sprint     → Sprint Prioritizer — backlog grooming
```

---

*Generated: 2026-05-14 | Source: github.com/msitarzewski/agency-agents | 184 agents + 58 short aliases*
