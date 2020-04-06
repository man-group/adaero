import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { FeedbackUserListComponent } from './feedback-user-list.component';

describe('FeedbackUserListComponent', () => {
  let component: FeedbackUserListComponent;
  let fixture: ComponentFixture<FeedbackUserListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ FeedbackUserListComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(FeedbackUserListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
