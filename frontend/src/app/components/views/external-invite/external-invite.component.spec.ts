import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ExternalInviteComponent } from './external-invite.component';

describe('ExternalInviteComponent', () => {
  let component: ExternalInviteComponent;
  let fixture: ComponentFixture<ExternalInviteComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ExternalInviteComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ExternalInviteComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
