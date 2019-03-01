import { TestBed, inject } from '@angular/core/testing';
import { HttpClientModule } from '@angular/common/http';
import { RouterTestingModule } from '@angular/router/testing';
import { FormsModule } from '@angular/forms';

import { AppRoutingModule } from '../app-routing.module';
import { AnonGuardService } from './anon-guard.service';
import { ApiService } from '../services/api.service';
import {
  GiveFeedbackComponent,
  NomineesListComponent,
  LoginComponent,
  SelfNominateComponent
} from '../components';

describe('AnonGuardService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [
        LoginComponent,
        NomineesListComponent,
        GiveFeedbackComponent,
        SelfNominateComponent
      ],
      imports: [
        FormsModule,
        HttpClientModule,
        RouterTestingModule
      ],
      providers: [
        AnonGuardService,
        ApiService
      ]
    });
  });

  it('should be created', inject([AnonGuardService], (service: AnonGuardService) => {
    expect(service).toBeTruthy();
  }));
});
