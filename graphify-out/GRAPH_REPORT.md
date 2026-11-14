# Graph Report - tapserve  (2026-11-13)

## Corpus Check
- 340 files · ~186,610 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: .css 9, (none) 4, .example 2)

## Summary
- 2701 nodes · 9581 edges · 132 communities (90 shown, 42 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1027 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `423e767c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Checklist por cena (29 itens)
- ServiceRequests.tsx
- django_db
- request
- NfcConfigurator.tsx
- CustomerWorkspace.tsx
- django_db_models_deletion
- urls.py
- RealtimeConnection
- customer
- test_mfa.py
- test_interface_update.py
- realtime.py
- access/views.py
- api.py
- Operation.tsx
- operational.test.mjs
- test_client_experience_update.py
- demo.py
- video.py
- Project Operations Documentation
- app/App.tsx
- test_client_experience_update.py
- DeviceAccess
- record
- ItemOutput
- Build and Secret Validation
- PlatformScreen.tsx
- site/package.json
- test_operational_performance.py
- catalog/views.py
- pytest
- test_update.py
- TapServe — Asset Sheet completo V3
- local_env.py
- 4. Sitemap e especificação de TODAS as páginas
- ManualOrder.tsx
- customer-refinement.mjs
- compilerOptions
- ReasonInput
- Frontend Build Dependencies
- TypeScript Compiler Options
- 4. Páginas internas — roteiro completo
- ProductPhoto
- test_local_environments.py
- workspace_media
- identity/views.py
- setup_platform.py
- Disposable PostgreSQL Laboratory
- Authentication Schema Configuration
- Prompts finais
- Refinamento da landing page TapServe — 13/11/2026
- orders/views.py
- ui-regressions.mjs
- browser.mjs
- AuditEvent
- mfa.py
- AuditEvent
- ref_node_fs
- secrets
- qa_node_probe.mjs
- Anexo de tratamento de dados pessoais — minuta
- Socket
- mfa.test.mjs
- README.md
- TapServe Wordmark Design
- French Fries Demo Image
- pages.tsx
- verify_environment.py
- 13. Conformidade jurídica e proteção de dados — instruções obrigatórias para criação das páginas legais
- Cheeseburger Demo Image
- Citrus Drink Demo Image
- Contactless Brand Icon
- TapServe — Arquitetura do Site Institucional e Comercial
- Refinamento final da landing page TapServe — 13/11/2026
- Form
- 5. Inventário fechado de produção visual (59 entregáveis planejados)
- Política de Privacidade — minuta de trabalho
- Product
- tsconfig.ui-tests.json
- Instrumento de assinatura TapServe — minuta separada
- 11. Entregas em ordem de execução
- site/vite.config.js
- subprocess
- ProbeClient
- 1. Identidade, layout e fotografia
- 8. Comportamento responsivo
- Termos de Uso do site institucional — minuta
- 2. Navegação pública (sitemap)
- Auditoria jurídica e de dados — TapServe
- Cancelamento e reembolso — minuta
- Execução do site TapServe V3
- .get
- Matriz de páginas e experiência
- test_v2_migrations.py
- test_api_404_is_json_without_masking_auth_or_valid_endpoints
- Prompts e produção de imagens — TapServe V3
- ServicePoint
- frontend/tests/contrast.test.mjs
- admission.py
- Input
- SpaHandler
- 0005_product_applied_option_groups_and_more.py
- 0005_production_guards.py
- Entrega do site TapServe V3
- 0014_remove_servicerequest_request_kind_valid_and_more.py
- 0005_unit_menu_layout_unit_unit_menu_layout_valid.py
- QA técnico — 13/11/2026
- uuid

## God Nodes (most connected - your core abstractions)
1. `post_with_csrf()` - 130 edges
2. `request()` - 118 edges
3. `AuditEvent` - 110 edges
4. `owner_client()` - 100 edges
5. `customer()` - 94 edges
6. `record()` - 94 edges
7. `OrderItem` - 87 edges
8. `CookieMutationAPIView` - 78 edges
9. `ServicePoint` - 75 edges
10. `payload()` - 74 edges

## Surprising Connections (you probably didn't know these)
- `Funcionalidades e alegações comerciais` --references--> `Company`  [INFERRED]
  docs/site/LEGAL_AUDIT.md → backend/apps/organizations/models.py
- `Demonstração fiel e isolada` --references--> `ProductImage()`  [INFERRED]
  site/README.md → frontend/src/components/Interface.tsx
- `Auditoria visual e funcional concluída` --references--> `decode()`  [INFERRED]
  docs/site/REFINAMENTO_FINAL_LANDING_2026-11-13.md → frontend/src/features/staff/SectorAssignments.tsx
- `5. Canais oficiais e comportamento de CTAs` --references--> `text()`  [INFERRED]
  assets_source/TAPSERVE_SUPERPROMPT_UNICO_CODEX_V3.md → frontend/src/lib/api.ts
- `Origem e fidelidade das interfaces` --references--> `ServiceRequests()`  [INFERRED]
  docs/site/REFINAMENTO_LANDING_2026-11-13.md → frontend/src/features/customer/ServiceRequests.tsx

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DEV QA logical environment isolation** — docs_ambientes_locais_dev, docs_ambientes_locais_qa, docs_ambientes_locais_destination_guard, docs_ambientes_locais_session_isolation [EXTRACTED 1.00]
- **Safe additive seed preservation** — docs_seeds_dev_qa_environment_seed, docs_seeds_dev_qa_idempotent_preservation, docs_seeds_dev_qa_seed_manifest, docs_seeds_dev_qa_credential_vault [EXTRACTED 1.00]
- **Tenant-scoped restaurant service** — readme_tapserve, readme_customer_access, readme_staff_roles, readme_tenant_isolation [EXTRACTED 1.00]

## Communities (132 total, 42 thin omitted)

### Community 0 - "Checklist por cena (29 itens)"
Cohesion: 0.06
Nodes (34): Checklist por cena (29 itens), D01 — Hambúrguer (P0), D02 — Batata frita (P0), D03 — Refrigerante (P0), D04 — Água (P0), D05 — Brownie (P0), D06 — Milk-shake (P0), D07 — Sanduíche de frango (P0) (+26 more)

### Community 1 - "ServiceRequests.tsx"
Cohesion: 0.08
Nodes (31): ActionNotice, ActionPopup(), Feedback(), Modal(), PendingChanges(), Call, CallAction(), submit() (+23 more)

### Community 2 - "django_db"
Cohesion: 0.04
Nodes (32): Migration, Migration, Migration, Migration, Migration, normalize_image(), Migration, Migration (+24 more)

### Community 3 - "request"
Cohesion: 0.09
Nodes (62): ConfirmDialog(), Toast(), update(), Photo, submit(), active, available, CatalogManagement() (+54 more)

### Community 4 - "NfcConfigurator.tsx"
Cohesion: 0.26
Nodes (12): lockTag(), nfcCapabilities(), nfcError(), NfcReader, Reading, verifyTag(), Window, writeTag() (+4 more)

### Community 5 - "CustomerWorkspace.tsx"
Cohesion: 0.07
Nodes (80): Origem e fidelidade das interfaces, Validações e evidências, FulfillmentSelector(), Button(), CustomerHeader(), EmptyState(), Icon(), ParticipantChip() (+72 more)

### Community 6 - "django_db_models_deletion"
Cohesion: 0.05
Nodes (17): Migration, Migration, Migration, Migration, revoke_legacy_access(), Migration, Migration, Migration (+9 more)

### Community 7 - "urls.py"
Cohesion: 0.08
Nodes (37): AdmissionClaimView, AdmissionDecisionView, RevokePointDevicesView, StaffAdmissionsView, CanManagePoints, PointMenuOptionDetailView, PointMenuOptionsView, CanManageMenu (+29 more)

### Community 9 - "customer"
Cohesion: 0.11
Nodes (40): OrderBatch, Channel, Meta, OrderItem, Fulfillment, Meta, State, ServiceSession (+32 more)

### Community 10 - "test_mfa.py"
Cohesion: 0.25
Nodes (14): totp(), complete_mfa(), enrollment_code(), password_login(), test_failed_mfa_attempts_persist_rate_limit_and_csrf_stays_required(), test_mfa_challenges_expire_and_password_changes_invalidate_them(), test_mfa_replacement_revokes_other_sessions_only_after_new_factor_confirmed(), test_offline_recovery_reauthenticates_and_revokes_existing_sessions() (+6 more)

### Community 11 - "test_interface_update.py"
Cohesion: 0.11
Nodes (16): change_item(), ItemEditInput, StaffItemEditInput, Audience, test_catalog_invalidation_is_point_scoped_and_rolled_back(), test_product_image_revalidation_rechecks_access_and_availability(), test_two_simultaneous_item_edits_have_one_winner(), act() (+8 more)

### Community 12 - "realtime.py"
Cohesion: 0.05
Nodes (21): active_device(), DeviceAuthentication, acquire(), audience(), connection_parameters(), DomainConsumer, listen(), renew() (+13 more)

### Community 13 - "access/views.py"
Cohesion: 0.07
Nodes (30): admission_data(), AccessInput, DeviceOutput, Meta, IdentifierInput, PointInput, PointOutput, Meta (+22 more)

### Community 14 - "api.py"
Cohesion: 0.10
Nodes (8): CsrfSerializer, CsrfView, HealthSerializer, HealthView, not_found(), server_error(), client_address(), require_pin_network()

### Community 15 - "Operation.tsx"
Cohesion: 0.13
Nodes (37): FulfillmentBadge(), ErrorState(), LoadingSkeleton(), useSuccessToast(), decodeBatches(), DeliveryAction(), ItemContent(), Operation() (+29 more)

### Community 16 - "operational.test.mjs"
Cohesion: 0.10
Nodes (32): AccountMenu(), AdminLayout(), AttendantLayout(), UnitSelector(), select(), MobileNavigation(), adminNavigation, attendantNavigation (+24 more)

### Community 17 - "test_client_experience_update.py"
Cohesion: 0.10
Nodes (33): digest(), assert_no_refresh(), test_committed_event_and_trigger_are_visible_on_independent_connection(), test_listener_failure_is_logged_closed_and_next_connection_resubscribes(), scenario(), unavailable(), test_live_listener_disconnect_closes_sockets_and_reconnect_uses_one_subscription(), capture() (+25 more)

### Community 18 - "demo.py"
Cohesion: 0.10
Nodes (34): point_url(), delete_image(), save_image(), admitted_device(), advance(), atomic_write(), browser_request(), call() (+26 more)

### Community 19 - "video.py"
Cohesion: 0.10
Nodes (16): inspect_mp4(), visit(), inspect_video(), inspect_webm(), MediaReader, validate_video(), video_response(), chunks() (+8 more)

### Community 20 - "Project Operations Documentation"
Cohesion: 0.09
Nodes (31): AI-generated burger fries lemonade menu photos, Validated WEBP product image API, Channels 4.3.2 Daphne 4.2.3 asgiref 3.12.1, Pinned Python runtime dependencies, Argon2 25.1.0 cryptography 50.0.2, Pytest Ruff Mypy pip-audit Bandit dependencies, Explicit environment and database destination validation, DEV tapserve_dev role tapserve_dev_user ports 8004 5177 (+23 more)

### Community 21 - "app/App.tsx"
Cohesion: 0.12
Nodes (15): App(), CustomerScreen, HealthScreen(), PlatformScreen, StaffScreen, Status, ErrorBoundary, NotFound() (+7 more)

### Community 22 - "test_client_experience_update.py"
Cohesion: 0.12
Nodes (14): connected_devices(), RealtimeLease, Meta, RequestBoundaryMiddleware, test_check_request_uses_existing_queue_and_session_idempotently(), test_closed_session_authorizations_do_not_fill_the_next_service(), test_configured_video_upload_limit_is_enforced_even_above_eight_digits(), test_http_activity_keeps_a_slot_but_pending_socket_is_not_connected() (+6 more)

### Community 23 - "DeviceAccess"
Cohesion: 0.13
Nodes (20): DeviceAccess, Meta, StaffIdentity, identity(), approve_request(), test_access_is_bound_idempotent_and_has_no_staff_privilege(), test_copied_static_url_needs_separate_staff_consent_for_each_browser(), test_expiry_revocation_and_point_status_are_checked_each_request() (+12 more)

### Community 24 - "record"
Cohesion: 0.07
Nodes (59): CustomerScreen(), poll(), CustomerWorkspace(), addParticipant(), load(), navigate(), notify(), orders() (+51 more)

### Community 25 - "ItemOutput"
Cohesion: 0.08
Nodes (14): SectorOutput, Meta, ItemCancelInput, OrderingSettingsInput, OrderPolicyInput, policy_data(), PublicItemCancelView, PublicItemView (+6 more)

### Community 26 - "Build and Secret Validation"
Cohesion: 0.11
Nodes (11): Migration, number_existing_tables(), findings(), main(), validate_traceability(), EntryAssets, inspect_bundle(), main() (+3 more)

### Community 27 - "PlatformScreen.tsx"
Cohesion: 0.21
Nodes (16): SecretInput(), Challenge, decodeChallenge(), MfaChallenge(), submit(), MfaSettings(), change(), replace() (+8 more)

### Community 28 - "site/package.json"
Cohesion: 0.06
Nodes (39): dependencies, react@19.3.0, react-dom@19.3.0, devDependencies, eslint@10.11.0, playwright@1.62.1, @types/react@19.3.0, @types/react-dom@19.3.0 (+31 more)

### Community 29 - "test_operational_performance.py"
Cohesion: 0.14
Nodes (4): test_customer_profile(), test_committed_order_notifies_two_independent_native_asgi_processes(), scenario(), test_operational_profile()

### Community 30 - "catalog/views.py"
Cohesion: 0.07
Nodes (32): PublicView, PublicProductPhotoView, search_catalog(), CategoryOutput, Meta, ImageInput, ProductOutput, Meta (+24 more)

### Community 31 - "pytest"
Cohesion: 0.14
Nodes (19): test_point_admin_is_scoped_and_creation_is_idempotent(), test_images_are_reencoded_and_invalid_content_is_rejected(), test_database_blocks_cross_unit_roles_and_audit_mutation(), test_lab_backup_never_overwrites_existing_archive(), test_lab_restore_rejects_non_disposable_or_nonlocal_configuration(), test_production_examples_preserve_transport_and_token_log_boundaries(), test_forwarded_client_address_requires_explicit_proxy_trust(), test_pin_is_denied_outside_allowed_network_and_forged_headers_do_not_bypass() (+11 more)

### Community 32 - "test_update.py"
Cohesion: 0.11
Nodes (34): ItemCommand, StaffItemCancelInput, DomainEvent, Meta, ItemStatusEvent, ProductionAssignment, Meta, StatusInput (+26 more)

### Community 33 - "TapServe — Asset Sheet completo V3"
Cohesion: 0.10
Nodes (19): 0. Prioridade real: o que VOCÊ precisa disponibilizar primeiro, 1. Regras de produção, 2. Lista detalhada — os 70 materiais, 3. Detalhamento especial da animação NFC (HOME e COMO FUNCIONA), 4. Demonstração interativa do pedido (`/demonstracao`), 5. Outros arquivos e informações que NÃO são imagens, 6. Estrutura sugerida para disponibilizar ao Codex, 7. Ordem de produção (para economizar trabalho) (+11 more)

### Community 34 - "local_env.py"
Cohesion: 0.20
Nodes (13): check_database(), clean_environment(), create_test_database(), initialize(), load(), main(), parameters(), read_env() (+5 more)

### Community 35 - "4. Sitemap e especificação de TODAS as páginas"
Cohesion: 0.07
Nodes (28): 0. Hierarquia das fontes, escopo e restrições, 1. Objetivo e conceito criativo, 2. Plano de execução contínua (faça tudo em sequência), 3. Padrão de assets e uso da plaquinha fornecida, 4.0 Navegação e componentes globais, 4.10 `/duvidas`, 4.11 `/sobre`, 4.12 `/privacidade` (+20 more)

### Community 36 - "ManualOrder.tsx"
Cohesion: 0.10
Nodes (23): normalizeSearch(), SearchCombobox(), submit(), SearchSuggestion, afterFailedSubmission(), decodeCart(), emptyCart(), orderPayload() (+15 more)

### Community 37 - "customer-refinement.mjs"
Cohesion: 0.13
Nodes (14): batches, calls, id, itemId, itemWrites, orderItem, output, person (+6 more)

### Community 38 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, exactOptionalPropertyTypes, isolatedModules, jsx, lib, module, moduleResolution (+11 more)

### Community 39 - "ReasonInput"
Cohesion: 0.24
Nodes (3): ReasonInput, DeviceRevokeView, CatalogSchema

### Community 40 - "Frontend Build Dependencies"
Cohesion: 0.06
Nodes (38): dependencies, react@19.3.0, react-dom@19.3.0, devDependencies, eslint@10.11.0, playwright@1.62.1, @types/react@19.3.0, @types/react-dom@19.3.0 (+30 more)

### Community 41 - "TypeScript Compiler Options"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, exactOptionalPropertyTypes, isolatedModules, jsx, lib, module, moduleResolution (+11 more)

### Community 42 - "4. Páginas internas — roteiro completo"
Cohesion: 0.11
Nodes (18): 4. Páginas internas — roteiro completo, P01 — Como funciona (`/como-funciona`), P02 — Funcionalidades (`/funcionalidades`), P03 — NFC e QR Code (`/nfc-e-qr-code`), P04 — Para quem é (`/para-quem`) [P1], P05 — Planos (`/planos`), P06 — Demonstração (`/demonstracao`), P07 — Contato (`/contato`) (+10 more)

### Community 43 - "ProductPhoto"
Cohesion: 0.15
Nodes (11): PhotoMetadataInput, PhotoUploadInput, ProductPhotosView, ProductPhotoView, PhotoOutput, Meta, publish_catalog_change(), write_product() (+3 more)

### Community 44 - "test_local_environments.py"
Cohesion: 0.10
Nodes (5): launcher(), test_lan_launcher_preserves_both_origins_and_uses_first_for_qr(), test_lan_launcher_rejects_non_private_or_unspecified_advertised_addresses(), profiles(), test_seed_refuses_nonlocal_settings_before_database_or_credential_access()

### Community 46 - "identity/views.py"
Cohesion: 0.11
Nodes (28): Staff, Meta, CanManageStaff, ContextOutput, ListQuery, PasswordLoginInput, PinLoginInput, RoleOutput (+20 more)

### Community 48 - "Disposable PostgreSQL Laboratory"
Cohesion: 0.35
Nodes (13): check_identity(), environment(), main(), notify(), parameters(), prepare(), run(), save() (+5 more)

### Community 49 - "Authentication Schema Configuration"
Cohesion: 0.14
Nodes (5): IdentityConfig, DeviceCookieScheme, PlatformCookieScheme, StaffCookieScheme, OrganizationsConfig

### Community 50 - "Prompts finais"
Cohesion: 0.10
Nodes (20): D01 — D01-demo-burger, D02 — D02-demo-fries, D03 — D03-demo-soda, D04 — D04-demo-water, D05 — D05-demo-brownie, D06 — D06-demo-milkshake, D07 — D07-demo-chicken, D08 — D08-demo-salad (+12 more)

### Community 51 - "Refinamento da landing page TapServe — 13/11/2026"
Cohesion: 0.33
Nodes (6): Alterações implementadas, Animações e microinterações, Arquivos e finalidade, Estado da entrega, Pendências reais e limites, Refinamento da landing page TapServe — 13/11/2026

### Community 52 - "orders/views.py"
Cohesion: 0.08
Nodes (30): live_devices(), work_items(), BatchOutput, Meta, ManualOrderInput, OrderInput, OrderLineInput, OrderReceiptOutput (+22 more)

### Community 53 - "ui-regressions.mjs"
Cohesion: 0.18
Nodes (7): call, cancellations, concurrentPolicy, errors, launchers, policy, writes

### Community 54 - "browser.mjs"
Cohesion: 0.25
Nodes (8): auditInteractions(), auditPages(), evidence, headers, output, rpc(), run(), auditMediaAndLoader()

### Community 55 - "AuditEvent"
Cohesion: 0.10
Nodes (45): Permission, Role, Meta, SelectedOption, Meta, test_menu_summary_uses_canonical_point_identification(), patch(), test_identifier_and_presence_permissions_are_scoped() (+37 more)

### Community 56 - "mfa.py"
Cohesion: 0.09
Nodes (25): resolve_staff(), StaffSessionAuthentication, Command, audit(), begin_challenge(), challenge_data(), change_credential(), finish_challenge() (+17 more)

### Community 57 - "AuditEvent"
Cohesion: 0.07
Nodes (58): _decide_admission(), invalidate_admissions(), change_point(), configure_identifier(), create_point(), revoke_device(), AuditEvent, Meta (+50 more)

### Community 58 - "ref_node_fs"
Cohesion: 0.22
Nodes (4): errors, output, pending, state

### Community 59 - "secrets"
Cohesion: 0.08
Nodes (25): Command, configure_unit(), PlatformAuditEvent, PlatformOperator, CompanyInput, CompanyOutput, Meta, IsPlatformOperator (+17 more)

### Community 60 - "qa_node_probe.mjs"
Cohesion: 0.20
Nodes (5): output, parent, report, root, { values }

### Community 61 - "Anexo de tratamento de dados pessoais — minuta"
Cohesion: 0.17
Nodes (11): 10. Responsabilidades, revisão e aceite, 1. Partes e papéis por finalidade, 2. Objeto, categorias e instruções, 3. Deveres do estabelecimento e do fornecedor, 4. Dados sensíveis e menores, 5. Segurança e evidências, 6. Suboperadores e transferências internacionais, 7. Direitos dos titulares e solicitações de autoridades (+3 more)

### Community 64 - "README.md"
Cohesion: 0.20
Nodes (6): Manifesto completo de assets V3, Assets e publicação, Demonstração fiel e isolada, Execução local, TapServe — site comercial, Verificação

### Community 65 - "TapServe Wordmark Design"
Cohesion: 0.50
Nodes (4): Bold black TapServe lettering, Contactless card symbol, TapServe brand, TapServe wordmark

### Community 66 - "French Fries Demo Image"
Cohesion: 0.67
Nodes (3): French fries, Ketchup accompaniment, French fries photograph

### Community 67 - "pages.tsx"
Cohesion: 0.11
Nodes (41): App(), Demo(), DesktopScreen(), journey, Journey(), NfcPlaque(), OperationFlow(), PhonePreview() (+33 more)

### Community 68 - "verify_environment.py"
Cohesion: 0.29
Nodes (6): Command, client(), order(), complete_mfa(), expect(), post()

### Community 69 - "13. Conformidade jurídica e proteção de dados — instruções obrigatórias para criação das páginas legais"
Cohesion: 0.15
Nodes (13): 13.10 Regras estritas para Codex/IA elaborar textos jurídicos, 13.11 Checklist de bloqueio de publicação das páginas legais, 13.12 Referências oficiais para consulta e verificação na data da redação, 13.1 Normas e fontes que precisam ser conferidas na redação, 13.2 Levantamento obrigatório ANTES de redigir qualquer política ou termo, 13.3 Política de Privacidade (`/privacidade`) — tópicos mínimos, 13.4 Relação TapServe × estabelecimentos: papéis, contratos e instruções, 13.5 Termos de Uso do site (`/termos`) versus contrato de assinatura (+5 more)

### Community 91 - "TapServe — Arquitetura do Site Institucional e Comercial"
Cohesion: 0.18
Nodes (10): 0. Decisão central de produto e posicionamento, 10. Conteúdo e limites do que podemos afirmar, 12. Insumos necessários para produzir os materiais reais, 3. HOME (`/`) — roteiro de 13 seções, 6. Matriz de imagem por página, 7. Regras de animação e interação, 9. Arquitetura técnica sugerida, Cinco momentos especiais (+2 more)

### Community 92 - "Refinamento final da landing page TapServe — 13/11/2026"
Cohesion: 0.25
Nodes (8): Alterações implementadas, Auditoria visual e funcional concluída, Causas e correções das imagens, Limites e publicação, Principais arquivos modificados, Refinamento final da landing page TapServe — 13/11/2026, Status, Verificação já concluída

### Community 94 - "5. Inventário fechado de produção visual (59 entregáveis planejados)"
Cohesion: 0.29
Nodes (7): 5.1 Identidade — 6 arquivos, 5.2 Fotografia e produto físico — 18 originais, 5.3 Capturas reais de interface — 20 telas, 5.4 Composições publicitárias — 6 arquivos, 5.5 Animações/vídeos — 4 entregáveis (poster + vídeo comprimido), 5.6 Compartilhamento social — 5 arquivos, 5. Inventário fechado de produção visual (59 entregáveis planejados)

### Community 95 - "Política de Privacidade — minuta de trabalho"
Cohesion: 0.18
Nodes (10): 1. Quem trata os dados e o que este documento abrange, 2. Navegação e demonstração do site, 3. Contatos iniciados pelo visitante, 4. Dados na plataforma operacional, 5. Compartilhamento e transferências, 6. Conservação e eliminação, 7. Direitos e como encaminhar uma solicitação, 8. Segurança e incidentes (+2 more)

### Community 97 - "Product"
Cohesion: 0.06
Nodes (47): Migration, Category, Meta, Menu, Option, Meta, OptionGroup, Meta (+39 more)

### Community 98 - "tsconfig.ui-tests.json"
Cohesion: 0.50
Nodes (3): extends, include, ./tsconfig.json

### Community 99 - "Instrumento de assinatura TapServe — minuta separada"
Cohesion: 0.20
Nodes (9): 1. Partes, representação e documentos, 2. Objeto e limites verificáveis, 3. Plano, capacidade e preço, 4. Ciclo, cobrança e alterações, 5. Implantação, responsabilidades e suporte, 6. Acesso, segurança e dados, 7. Suspensão, encerramento e saída, 8. Propriedade intelectual, responsabilidade e revisão (+1 more)

### Community 101 - "11. Entregas em ordem de execução"
Cohesion: 0.40
Nodes (5): 11. Entregas em ordem de execução, Fase A — Base verdadeira, Fase B — Arte e layout, Fase C — Desenvolvimento comercial, Fase D — Qualidade e publicação

### Community 102 - "site/vite.config.js"
Cohesion: 0.15
Nodes (5): root, server, types, catalogue, root

### Community 103 - "subprocess"
Cohesion: 0.13
Nodes (7): configure_local_tokens(), main(), main(), inspect_token_and_pipe(), handle_security(), sddl(), probe()

### Community 105 - "1. Identidade, layout e fotografia"
Cohesion: 0.50
Nodes (4): 1. Identidade, layout e fotografia, Card físico — regra visual obrigatória, Linguagem, Paleta

### Community 106 - "8. Comportamento responsivo"
Cohesion: 0.50
Nodes (4): 8. Comportamento responsivo, Desktop (≥ 1024 px), Mobile (320–767 px), Tablet (768–1023 px)

### Community 107 - "Termos de Uso do site institucional — minuta"
Cohesion: 0.20
Nodes (9): 1. Responsável e finalidade, 2. Conteúdo comercial, 3. Demonstração interativa, 4. Uso permitido e integridade, 5. Marca, conteúdo e imagens, 6. Links e aplicativos externos, 7. Privacidade, disponibilidade e responsabilidade, 8. Contato, versão e solução de questões (+1 more)

### Community 108 - "2. Navegação pública (sitemap)"
Cohesion: 0.67
Nodes (3): 2. Navegação pública (sitemap), Canais oficiais — regra obrigatória para todo o site, O que lançar primeiro

### Community 109 - "Auditoria jurídica e de dados — TapServe"
Cohesion: 0.25
Nodes (8): Auditoria jurídica e de dados — TapServe, Bloqueio de lançamento e revisão, Capturas reais e acesso seguro, Escopo e método, Fontes oficiais consultadas em 13/11/2026, Funcionalidades e alegações comerciais, Inventário do site e decisão sobre cookies, Matriz de tratamento

### Community 110 - "Cancelamento e reembolso — minuta"
Cohesion: 0.22
Nodes (8): 1. Escopo e responsável, 2. Como iniciar uma solicitação, 3. Efeito, renovação e cobrança, 4. Arrependimento, reembolso e cobranças discutidas, 5. Implantação e material físico, 6. Dados após o encerramento, 7. Aprovação e consistência, Cancelamento e reembolso — minuta

### Community 111 - "Execução do site TapServe V3"
Cohesion: 0.25
Nodes (7): Conferências e ajustes finais, Decisões e conflitos registrados antes da implementação, Direção de arte, Execução do site TapServe V3, Fases em sequência, Fontes e escopo, Segurança da implementação

### Community 113 - ".get"
Cohesion: 0.40
Nodes (3): HistoryQuery, SessionHistoryOutput, Meta

### Community 115 - "Matriz de páginas e experiência"
Cohesion: 0.50
Nodes (3): Conferência da fase 1, Matriz de páginas e experiência, Motion planejado

### Community 119 - "ServicePoint"
Cohesion: 0.07
Nodes (25): DeviceAdmission, Meta, ServicePoint, Kind, Meta, Command, Command, Migration (+17 more)

### Community 120 - "frontend/tests/contrast.test.mjs"
Cohesion: 0.67
Nodes (3): contrast(), css, luminance()

### Community 121 - "admission.py"
Cohesion: 0.12
Nodes (13): admission_for(), AdmissionDecision, AdmissionOutput, Meta, AdmissionPollView, AdmissionQuery, decide_admission(), NfcActionInput (+5 more)

### Community 126 - "Entrega do site TapServe V3"
Cohesion: 0.25
Nodes (8): Antes do lançamento, Demo e canais, Entrega do site TapServe V3, Imagens e arte original, Jurídico e comercial, Motion e interação, Páginas, Testes e execução local

### Community 130 - "QA técnico — 13/11/2026"
Cohesion: 0.18
Nodes (7): O que o proprietário precisa confirmar antes do lançamento, Acessibilidade e performance, Navegador e inspeção visual: PENDENTES, O que os testes da demo provaram, QA técnico — 13/11/2026, Reprodução, Resultados observados

### Community 138 - "uuid"
Cohesion: 0.08
Nodes (20): ProductPhoto, Meta, test_customer_confirmation_appears_in_staff_operation_over_http(), call(), test_abandon_and_late_manual_submission_serialize_without_duplicate(), send(), test_policy_http_conflict_preserves_winner_and_allows_explicit_rebase(), edit() (+12 more)

## Knowledge Gaps
- **19 isolated node(s):** `./tsconfig.json`, `Validated WEBP product image API`, `Argon2 25.1.0 cryptography 50.0.2`, `Pytest Ruff Mypy pip-audit Bandit dependencies`, `Staff-declared external receipt and reversal` (+14 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 918 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **42 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Auditoria jurídica e de dados — TapServe` connect `Auditoria jurídica e de dados — TapServe` to `QA técnico — 13/11/2026`?**
  _High betweenness centrality (0.300) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `post_with_csrf()` (e.g. with `scenario()` and `scenario()`) actually correct?**
  _`post_with_csrf()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `./tsconfig.json`, `Validated WEBP product image API`, `Argon2 25.1.0 cryptography 50.0.2` to the rest of the system?**
  _19 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Checklist por cena (29 itens)` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **Why does `Company` connect `secrets` to `Product`, `django_db`, `Auditoria jurídica e de dados — TapServe`, `demo.py`, `ServicePoint`?**
  _High betweenness centrality (0.298) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `AuditEvent` (e.g. with `_decide_admission()` and `NfcAuthorizeView`) actually correct?**
  _`AuditEvent` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Should `ServiceRequests.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07673469387755102 - nodes in this community are weakly interconnected._