import { TestBed, inject } from '@angular/core/testing';

import { PendingChangesGuardService } from './pending-changes-guard.service';

describe('PendingChangesGuardService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PendingChangesGuardService]
    });
  });

  it('should be created', inject([PendingChangesGuardService], (service: PendingChangesGuardService) => {
    expect(service).toBeTruthy();
  }));
});
