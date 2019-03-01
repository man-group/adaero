import { TestBed, inject } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { AuthGuardService } from './auth-guard.service';
import { ApiService } from '../services/api.service';
import { HttpClientModule } from '@angular/common/http';

describe('AuthGuardService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ HttpClientModule, RouterTestingModule ],
      providers: [AuthGuardService, ApiService]
    });
  });

  it('should be created', inject([AuthGuardService], (service: AuthGuardService) => {
    expect(service).toBeTruthy();
  }));
});
