import { TestBed, inject } from '@angular/core/testing';

import { CookieService } from './cookie.service';

describe('CookieService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CookieService]
    });
  });

  it('should be created', inject([CookieService], (service: CookieService) => {
    expect(service).toBeTruthy();
  }));
});
