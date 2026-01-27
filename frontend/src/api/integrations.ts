import { Forge } from "./forge-axios";

export interface IntegrationWorkspace {
  id: number;
  name: string;
  status: string;
  editable: boolean;
}

export interface IntegrationStatus {
  id: number;
  keycloak_user_id: string;
  status: string;
  workspace?: IntegrationWorkspace;
}

export interface LinkIntegrationResponse {
  status: string;
  data: {
    status: string;
  };
}

class IntegrationsClient {
  static async getIntegrationStatus(platform: string): Promise<IntegrationStatus> {
    const response = await Forge.get<IntegrationStatus>(`/api/v1/integrations/${platform}/status`);
    return response.data;
  }

  static async linkIntegration(platform: string, workspace: string): Promise<LinkIntegrationResponse> {
    const response = await Forge.post<LinkIntegrationResponse>(`/api/v1/integrations/${platform}/link`, {
      workspace,
    });
    return response.data;
  }

  static async unlinkIntegration(platform: string): Promise<void> {
    await Forge.post(`/api/v1/integrations/${platform}/unlink`);
  }

  static async configureIntegration(
    platform: string,
    data: {
      workspace: string;
      webhookSecret: string;
      serviceAccountEmail: string;
      serviceAccountApiKey: string;
      isActive: boolean;
    }
  ): Promise<void> {
    await Forge.post(`/api/v1/integrations/${platform}/configure`, data);
  }

  static async validateIntegration(platform: string, workspace: string): Promise<LinkIntegrationResponse> {
    const response = await Forge.post<LinkIntegrationResponse>(`/api/v1/integrations/${platform}/validate`, {
      workspace,
    });
    return response.data;
  }
}

export default IntegrationsClient;
